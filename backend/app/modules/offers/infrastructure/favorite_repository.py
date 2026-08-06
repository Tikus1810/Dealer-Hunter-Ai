"""SQLAlchemy implementation of `FavoriteRepositoryProtocol` (Band 09/10)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.offers.domain.entities import Favorite
from app.modules.offers.infrastructure.models import FavoriteModel


def _to_entity(row: FavoriteModel) -> Favorite:
    return Favorite(
        id=row.id, user_id=row.user_id, offer_id=row.offer_id, created_at=row.created_at
    )


class SqlAlchemyFavoriteRepository:
    """Implements `FavoriteRepositoryProtocol` (app.modules.offers.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, favorite: Favorite) -> Favorite:
        row = FavoriteModel(id=favorite.id, user_id=favorite.user_id, offer_id=favorite.offer_id)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)

    async def remove(self, user_id: uuid.UUID, offer_id: uuid.UUID) -> None:
        stmt = delete(FavoriteModel).where(
            FavoriteModel.user_id == user_id, FavoriteModel.offer_id == offer_id
        )
        await self._session.execute(stmt)

    async def exists(self, user_id: uuid.UUID, offer_id: uuid.UUID) -> bool:
        stmt = select(FavoriteModel.id).where(
            FavoriteModel.user_id == user_id, FavoriteModel.offer_id == offer_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def list_for_user(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> list[Favorite]:
        offset = max(page - 1, 0) * page_size
        stmt = (
            select(FavoriteModel)
            .where(FavoriteModel.user_id == user_id)
            .order_by(FavoriteModel.created_at.desc(), FavoriteModel.id.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(row) for row in rows]

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count(FavoriteModel.id)).where(FavoriteModel.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one()
