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
