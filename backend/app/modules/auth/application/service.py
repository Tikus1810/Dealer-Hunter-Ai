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
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._settings = settings

    async def register(self, *, email: str, password: str) -> uuid.UUID:
        if await self._users.get_by_email(email) is not None:
            raise ConflictError("email is already registered", details={"email": email})

        user = User(id=uuid.uuid4(), email=email, password_hash=hash_password(password))
        created = await self._users.create(user)
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
        if not await self._refresh_tokens.is_valid(jti):
            raise UnauthorizedError("refresh token has been revoked or reused")

        # Rotate: each refresh token is single-use. Revoking it here means a
        # stolen-and-replayed token fails on its second use (Band 14).
        await self._refresh_tokens.revoke(jti)
        return await self._issue_token_pair(uuid.UUID(payload["sub"]))

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
