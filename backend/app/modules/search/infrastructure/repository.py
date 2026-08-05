"""SQLAlchemy implementation of `SearchProfileRepositoryProtocol` (Band 03/09).

Like the offers repository, this translates between the domain entity's
plain-string `category` code and the persisted `category_id` foreign key
(see `app.modules.offers.infrastructure.models` for why categories are
normalized into their own table).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.offers.infrastructure.models import CategoryModel
from app.modules.search.domain.entities import SearchProfile
from app.modules.search.infrastructure.models import SearchProfileModel


def _to_entity(row: SearchProfileModel, category_code: str | None) -> SearchProfile:
    return SearchProfile(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        category=category_code or "",
        keywords=row.keywords,
        min_price=float(row.min_price) if row.min_price is not None else None,
        max_price=float(row.max_price) if row.max_price is not None else None,
        min_deal_score=row.min_deal_score,
        notify_on_match=row.notify_on_match,
        is_active=row.is_active,
    )


class SqlAlchemySearchProfileRepository:
    """Implements `SearchProfileRepositoryProtocol`
    (app.modules.search.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _category_id_for(self, category_code: str) -> uuid.UUID:
        stmt = select(CategoryModel.id).where(CategoryModel.code == category_code)
        category_id = (await self._session.execute(stmt)).scalar_one_or_none()
        if category_id is None:
            raise NotFoundError(
                f"category '{category_code}' is not seeded", details={"category": category_code}
            )
        return category_id

    async def get_by_id(self, profile_id: uuid.UUID) -> SearchProfile | None:
        row = await self._session.get(SearchProfileModel, profile_id)
        if row is None:
            return None
        category = await self._session.get(CategoryModel, row.category_id)
        return _to_entity(row, category.code if category else None)

    async def list_active(self) -> list[SearchProfile]:
        stmt = (
            select(SearchProfileModel, CategoryModel.code)
            .outerjoin(CategoryModel, SearchProfileModel.category_id == CategoryModel.id)
            .where(SearchProfileModel.is_active.is_(True))
        )
        rows = (await self._session.execute(stmt)).all()
        return [_to_entity(row, code) for row, code in rows]

    async def create(self, profile: SearchProfile) -> SearchProfile:
        category_id = await self._category_id_for(profile.category) if profile.category else None
        row = SearchProfileModel(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            category_id=category_id,
            keywords=profile.keywords,
            min_price=profile.min_price,
            max_price=profile.max_price,
            min_deal_score=profile.min_deal_score,
            notify_on_match=profile.notify_on_match,
            is_active=profile.is_active,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row, profile.category or None)
