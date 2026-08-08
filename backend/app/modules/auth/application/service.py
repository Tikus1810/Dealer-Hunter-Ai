"""Auth application service — implements `AuthServiceProtocol`.

Pure use-case orchestration: no FastAPI, no SQLAlchemy. Depends only on
the `UserRepositoryProtocol` / `RefreshTokenRepositoryProtocol` ports and
`app.core.security`, so it is unit-testable without a database (Band 03:
Service Layer, Dependency Injection).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.modules.analytics.application.interfaces import AnalyticsCollectorProtocol
from app.modules.analytics.domain.taxonomy import AnalyticsEventName
from app.modules.auth.application.interfaces import RefreshTokenRepositoryProtocol
from app.modules.auth.domain.entities import TokenPair
from app.modules.users.application.interfaces import UserRepositoryProtocol
from app.modules.users.domain.entities import User

logger = get_logger(__name__)


class AuthService:
    def __init__(
        self,
        users: UserRepositoryProtocol,
        refresh_tokens: RefreshTokenRepositoryProtocol,
        settings: Settings,
        analytics: AnalyticsCollectorProtocol | None = None,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._settings = settings
        self._analytics = analytics

    async def register(self, *, email: str, password: str) -> uuid.UUID:
        if await self._users.get_by_email(email) is not None:
            raise ConflictError("email is already registered", details={"email": email})

        user = User(id=uuid.uuid4(), email=email, password_hash=hash_password(password))
        created = await self._users.create(user)
        await self._track(AnalyticsEventName.USER_REGISTERED, user_id=created.id)
        return created.id

    async def login(self, *, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            # Same error for "no such user" and "wrong password" — never leak
            # which one it was (Band 14: no user enumeration).
            raise UnauthorizedError("invalid email or password")
        if not user.is_active:
            raise ForbiddenError("this account has been deactivated")

        # Opportunistic rehash (Band 14: Security-Härtung — OWASP ASVS
        # 2.4.x credential storage hygiene): a hash created under older
        # Argon2 parameters gets upgraded transparently on the next
        # successful login, using the plaintext password this call already
        # has and is about to discard. Best-effort — a failure here must
        # never block a successful login the user is otherwise entitled to.
        if needs_rehash(user.password_hash):
            try:
                await self._users.update_password_hash(
                    user.id, password_hash=hash_password(password)
                )
            except Exception as exc:  # noqa: BLE001 — never fail login over this
                logger.error("password_rehash_failed", user_id=str(user.id), error=str(exc))

        return await self._issue_token_pair(user.id)

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(
                refresh_token, settings=self._settings, expected_type=TokenType.REFRESH
            )
        except InvalidTokenError as exc:
            raise UnauthorizedError("invalid or expired refresh token") from exc

        jti = payload["jti"]
        user_id = uuid.UUID(payload["sub"])

        # Reuse detection (Band 14): a *revoked* token being presented
        # again — as opposed to one that simply never existed or expired
        # — can only happen if someone other than the legitimate client is
        # replaying a stolen refresh token. The real rotation flow below
        # never re-presents a token it already exchanged, so this is
        # treated as a compromise signal: log out every session for this
        # user, not just reject the one replayed request.
        if await self._refresh_tokens.is_revoked(jti):
            await self._refresh_tokens.revoke_all_for_user(user_id)
            logger.warning("refresh_token_reuse_detected", user_id=str(user_id))
            raise UnauthorizedError("refresh token has been revoked or reused")

        if not await self._refresh_tokens.is_valid(jti):
            raise UnauthorizedError("invalid or expired refresh token")

        # Rotate: each refresh token is single-use. Revoking it here means a
        # stolen-and-replayed token fails on its second use (Band 14) — and
        # is exactly the "revoked token presented again" case the reuse
        # check above catches if it ever happens.
        await self._refresh_tokens.revoke(jti)
        return await self._issue_token_pair(user_id)

    async def logout(self, *, refresh_token: str) -> None:
        try:
            payload = decode_token(
                refresh_token, settings=self._settings, expected_type=TokenType.REFRESH
            )
        except InvalidTokenError:
            return  # already invalid — logout is idempotent, nothing to revoke
        await self._refresh_tokens.revoke(payload["jti"])

    async def _issue_token_pair(self, user_id: uuid.UUID) -> TokenPair:
        access_token = create_token(
            subject=str(user_id), token_type=TokenType.ACCESS, settings=self._settings
        )
        refresh_token = create_token(
            subject=str(user_id), token_type=TokenType.REFRESH, settings=self._settings
        )
        payload = decode_token(
            refresh_token, settings=self._settings, expected_type=TokenType.REFRESH
        )
        await self._refresh_tokens.store(
            user_id=user_id,
            jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def _track(self, event_name: AnalyticsEventName, *, user_id: uuid.UUID) -> None:
        """Best-effort (Band 15): analytics is an optional collaborator
        (`analytics=None` is the default, and every existing call site
        still works unchanged) — a tracking failure must never fail the
        auth flow it's observing."""
        if self._analytics is None:
            return
        try:
            await self._analytics.track(event_name.value, user_id=user_id, properties={})
        except Exception as exc:  # noqa: BLE001 — never fail the caller over this
            logger.error("analytics_track_failed", event_name=event_name.value, error=str(exc))
