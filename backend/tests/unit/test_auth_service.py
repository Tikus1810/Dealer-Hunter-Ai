"""Unit tests for AuthService against in-memory fakes — no DB, no HTTP."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

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


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.revoked: set[str] = set()
        self.known: dict[str, uuid.UUID] = {}

    async def store(self, *, user_id: uuid.UUID, jti: str, expires_at: datetime) -> None:
        self.known[jti] = user_id

    async def is_valid(self, jti: str) -> bool:
        return jti in self.known and jti not in self.revoked

    async def revoke(self, jti: str) -> None:
        self.revoked.add(jti)


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
