"""Unit tests for AuthService against in-memory fakes — no DB, no HTTP."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

import app.modules.auth.application.service as auth_service_module
from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import hash_password
from app.modules.auth.application.service import AuthService
from app.modules.users.domain.entities import User

ServiceFixture = tuple[AuthService, "FakeUserRepository", "FakeRefreshTokenRepository"]


class FakeUserRepository:
    def __init__(self) -> None:
        self.by_id: dict[uuid.UUID, User] = {}

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.by_id.values() if u.email == email), None)

    async def create(self, user: User) -> User:
        self.by_id[user.id] = user
        return user

    async def update(self, user: User) -> User:
        self.by_id[user.id] = user
        return user

    async def update_password_hash(self, user_id: uuid.UUID, *, password_hash: str) -> None:
        self.by_id[user_id].password_hash = password_hash


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.revoked: set[str] = set()
        self.known: dict[str, uuid.UUID] = {}

    async def store(self, *, user_id: uuid.UUID, jti: str, expires_at: datetime) -> None:
        self.known[jti] = user_id

    async def is_valid(self, jti: str) -> bool:
        return jti in self.known and jti not in self.revoked

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked

    async def revoke(self, jti: str) -> None:
        self.revoked.add(jti)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        self.revoked.update(jti for jti, owner in self.known.items() if owner == user_id)


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret_key="test-secret")


@pytest.fixture
def service(settings: Settings) -> ServiceFixture:
    users = FakeUserRepository()
    tokens = FakeRefreshTokenRepository()
    return AuthService(users, tokens, settings), users, tokens


async def test_register_then_login_succeeds(service: ServiceFixture) -> None:
    auth, _users, _tokens = service
    user_id = await auth.register(email="a@example.com", password="correcthorse")

    pair = await auth.login(email="a@example.com", password="correcthorse")

    assert pair.access_token
    assert pair.refresh_token
    assert user_id is not None


async def test_register_duplicate_email_raises_conflict(service: ServiceFixture) -> None:
    auth, _users, _tokens = service
    await auth.register(email="dup@example.com", password="correcthorse")

    with pytest.raises(ConflictError):
        await auth.register(email="dup@example.com", password="anotherpassword")


async def test_login_wrong_password_raises_unauthorized(service: ServiceFixture) -> None:
    auth, _users, _tokens = service
    await auth.register(email="b@example.com", password="correcthorse")

    with pytest.raises(UnauthorizedError):
        await auth.login(email="b@example.com", password="wrongpassword")


async def test_login_unknown_email_raises_unauthorized_not_not_found(
    service: ServiceFixture,
) -> None:
    auth, _users, _tokens = service
    with pytest.raises(UnauthorizedError):
        await auth.login(email="nobody@example.com", password="whatever1")


async def test_login_deactivated_account_raises_forbidden(service: ServiceFixture) -> None:
    auth, users, _tokens = service
    user_id = await auth.register(email="c@example.com", password="correcthorse")
    users.by_id[user_id].is_active = False

    with pytest.raises(ForbiddenError):
        await auth.login(email="c@example.com", password="correcthorse")


async def test_refresh_rotates_token_and_old_one_becomes_invalid(
    service: ServiceFixture,
) -> None:
    auth, _users, _tokens = service
    await auth.register(email="d@example.com", password="correcthorse")
    pair = await auth.login(email="d@example.com", password="correcthorse")

    new_pair = await auth.refresh(refresh_token=pair.refresh_token)
    assert new_pair.refresh_token != pair.refresh_token

    with pytest.raises(UnauthorizedError):
        await auth.refresh(refresh_token=pair.refresh_token)  # reuse of rotated token


async def test_refresh_reuse_of_a_rotated_token_revokes_every_session(
    service: ServiceFixture,
) -> None:
    """Reuse-detection (Band 14): replaying an already-rotated-out refresh
    token doesn't just fail the one request — it's treated as a signal the
    token was stolen, so every other still-valid session for that user
    gets logged out too, not just the replayed one."""
    auth, _users, tokens = service
    await auth.register(email="reuse@example.com", password="correcthorse")
    pair = await auth.login(email="reuse@example.com", password="correcthorse")
    rotated_pair = await auth.refresh(refresh_token=pair.refresh_token)

    with pytest.raises(UnauthorizedError):
        await auth.refresh(refresh_token=pair.refresh_token)  # replay the old, rotated token

    # The legitimately-rotated token is now also revoked — reuse detection
    # can't tell whether the attacker who replayed the old token also has
    # this one, so it invalidates the whole session rather than gamble.
    with pytest.raises(UnauthorizedError):
        await auth.refresh(refresh_token=rotated_pair.refresh_token)
    assert len(tokens.revoked) == 2  # both tokens for this user, none left valid


async def test_logout_revokes_refresh_token(service: ServiceFixture) -> None:
    auth, _users, _tokens = service
    await auth.register(email="e@example.com", password="correcthorse")
    pair = await auth.login(email="e@example.com", password="correcthorse")

    await auth.logout(refresh_token=pair.refresh_token)

    with pytest.raises(UnauthorizedError):
        await auth.refresh(refresh_token=pair.refresh_token)


async def test_logout_is_idempotent_for_already_invalid_token() -> None:
    settings = Settings(jwt_secret_key="test-secret")
    auth = AuthService(FakeUserRepository(), FakeRefreshTokenRepository(), settings)
    await auth.logout(refresh_token="not-a-real-token")  # must not raise


def test_hash_password_used_for_stored_credentials() -> None:
    # sanity check that the fixtures above exercise a real Argon2 hash, not a stub
    assert hash_password("x") != "x"


async def test_login_rehashes_password_when_current_hash_is_flagged_outdated(
    service: ServiceFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth, users, _tokens = service
    user_id = await auth.register(email="f@example.com", password="correcthorse")
    original_hash = users.by_id[user_id].password_hash

    # A real "outdated Argon2 parameters" hash can't be produced without a
    # second PasswordHasher config — monkeypatch the check itself instead,
    # same as this codebase's other tests that need a specific answer from
    # a pure function rather than reconstructing the conditions for it.
    monkeypatch.setattr(auth_service_module, "needs_rehash", lambda _hash: True)

    await auth.login(email="f@example.com", password="correcthorse")

    assert users.by_id[user_id].password_hash != original_hash


async def test_login_does_not_rehash_when_current_hash_is_up_to_date(
    service: ServiceFixture,
) -> None:
    auth, users, _tokens = service
    user_id = await auth.register(email="g@example.com", password="correcthorse")
    original_hash = users.by_id[user_id].password_hash

    await auth.login(email="g@example.com", password="correcthorse")

    assert users.by_id[user_id].password_hash == original_hash


class FakeAnalyticsCollector:
    def __init__(self) -> None:
        self.tracked: list[tuple[str, uuid.UUID | None]] = []

    async def track(
        self, event_name: str, *, user_id: uuid.UUID | None, properties: dict[str, object]
    ) -> None:
        self.tracked.append((event_name, user_id))


class FailingAnalyticsCollector:
    async def track(
        self, event_name: str, *, user_id: uuid.UUID | None, properties: dict[str, object]
    ) -> None:
        raise RuntimeError("analytics backend is down")


async def test_register_tracks_a_user_registered_event(settings: Settings) -> None:
    analytics = FakeAnalyticsCollector()
    auth = AuthService(
        FakeUserRepository(), FakeRefreshTokenRepository(), settings, analytics=analytics
    )

    user_id = await auth.register(email="i@example.com", password="correcthorse")

    assert analytics.tracked == [("user_registered", user_id)]


async def test_register_succeeds_even_if_analytics_tracking_fails(settings: Settings) -> None:
    auth = AuthService(
        FakeUserRepository(),
        FakeRefreshTokenRepository(),
        settings,
        analytics=FailingAnalyticsCollector(),
    )

    # Must not raise — a tracking failure must never block registration.
    user_id = await auth.register(email="j@example.com", password="correcthorse")
    assert user_id is not None


async def test_login_succeeds_even_if_rehash_persistence_fails(
    service: ServiceFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth, users, _tokens = service
    await auth.register(email="h@example.com", password="correcthorse")

    monkeypatch.setattr(auth_service_module, "needs_rehash", lambda _hash: True)

    async def failing_update(user_id: uuid.UUID, *, password_hash: str) -> None:
        raise RuntimeError("db is down")

    monkeypatch.setattr(users, "update_password_hash", failing_update)

    # Must not raise — a rehash failure must never block a login the user
    # is otherwise entitled to.
    pair = await auth.login(email="h@example.com", password="correcthorse")
    assert pair.access_token
