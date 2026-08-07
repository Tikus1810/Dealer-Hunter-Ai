"""Integration tests for SqlAlchemyUserRepository. Requires PostgreSQL (see conftest.py)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.entities import User
from app.modules.users.infrastructure.repository import SqlAlchemyUserRepository

pytestmark = pytest.mark.integration


def _make_user(email: str = "buyer@example.com") -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash="argon2-hash-placeholder",
        display_name="Test Buyer",
    )


async def test_create_then_get_by_id(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    created = await repo.create(_make_user())

    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.email == created.email
    assert fetched.roles == ["user"]


async def test_get_by_email_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    assert await repo.get_by_email("nobody@example.com") is None


async def test_update_persists_changes(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    created = await repo.create(_make_user("update-me@example.com"))

    created.display_name = "Renamed"
    updated = await repo.update(created)

    assert updated.display_name == "Renamed"


async def test_update_password_hash_persists_only_the_hash(db_session: AsyncSession) -> None:
    """Band 14: the opportunistic-rehash-on-login path
    (AuthService.login) — a separate method from update() precisely so it
    can't accidentally also overwrite display_name/is_active/roles from a
    stale User the caller only had for its password_hash."""
    repo = SqlAlchemyUserRepository(db_session)
    created = await repo.create(_make_user("rehash-me@example.com"))

    await repo.update_password_hash(created.id, password_hash="new-argon2-hash")

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.password_hash == "new-argon2-hash"
    assert fetched.display_name == created.display_name
