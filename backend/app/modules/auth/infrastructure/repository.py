"""SQLAlchemy implementation of `RefreshTokenRepositoryProtocol` (Band 03)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_factory
from app.modules.auth.infrastructure.models import RefreshTokenModel


class SqlAlchemyRefreshTokenRepository:
    """Implements `RefreshTokenRepositoryProtocol`
    (app.modules.auth.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store(self, *, user_id: uuid.UUID, jti: str, expires_at: datetime) -> None:
        self._session.add(RefreshTokenModel(user_id=user_id, token_jti=jti, expires_at=expires_at))
        await self._session.flush()

    async def is_valid(self, jti: str) -> bool:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_jti == jti)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            return False
        return row.expires_at > datetime.now(UTC)

    async def is_revoked(self, jti: str) -> bool:
        stmt = select(RefreshTokenModel.revoked_at).where(RefreshTokenModel.token_jti == jti)
        revoked_at = (await self._session.execute(stmt)).scalar_one_or_none()
        return revoked_at is not None

    async def revoke(self, jti: str) -> None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_jti == jti)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is not None and row.revoked_at is None:
            row.revoked_at = datetime.now(UTC)
            await self._session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Deliberately uses its own, independently-committed session
        instead of `self._session` (the ambient request-scoped one this
        repository otherwise always uses) — a real bug caught by
        `tests/integration/test_auth_api.py`'s reuse-detection test
        against real Postgres, not visible against the in-memory unit
        fake: `AuthService.refresh` calls this and then immediately
        `raise`s `UnauthorizedError`, and `app.db.session.get_db_session`'s
        unit-of-work **rolls back the whole request on any raised
        exception** (see that function's own docstring) — including this
        one. A same-session call here would have its revocation silently
        undone the moment the request fails, defeating the entire point
        of reuse detection. This is a security action that must survive
        independent of how the enclosing request resolves, the same
        reasoning `app/bootstrap.py`'s scheduler already uses
        `session_factory` directly instead of a request-scoped session
        for its own out-of-request-cycle writes."""
        async with session_factory() as session:
            stmt = (
                update(RefreshTokenModel)
                .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )
            await session.execute(stmt)
            await session.commit()
