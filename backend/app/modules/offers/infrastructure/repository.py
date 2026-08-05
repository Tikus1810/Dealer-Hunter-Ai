"""SQLAlchemy implementation of `OfferRepositoryProtocol` (Band 03/07).

Translates between the in-memory `Offer` entity (which carries the
`OfferCategory` enum) and the persisted `OfferModel` (which references
`categories.id`) — see the module docstring in `models.py` for why
categories are normalized into their own table.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.offers.infrastructure.models import CategoryModel, OfferModel


def _to_entity(row: OfferModel, category_code: str) -> Offer:
    return Offer(
        id=row.id,
        source=row.source,
        source_listing_id=row.source_listing_id,
        title=row.title,
        description=row.description,
        price_amount=float(row.price_amount),
        price_currency=row.price_currency,
        category=OfferCategory(category_code),
        images=list(row.images),
        location=row.location,
        seller_name=None,
        seller_rating=None,
        url=row.url,
        created_at=row.created_at,
        fetched_at=row.fetched_at,
    )


class SqlAlchemyOfferRepository:
    """Implements `OfferRepositoryProtocol` (app.modules.offers.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _category_id_for(self, category: OfferCategory) -> uuid.UUID:
        stmt = select(CategoryModel).where(CategoryModel.code == category.value)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise NotFoundError(
                f"category '{category.value}' is not seeded",
                details={"category": category.value},
            )
        return row.id

    async def get_by_id(self, offer_id: uuid.UUID) -> Offer | None:
        row = await self._session.get(OfferModel, offer_id)
        if row is None or row.is_deleted:
            return None
        category = await self._session.get(CategoryModel, row.category_id)
        assert category is not None  # FK guarantees existence
        return _to_entity(row, category.code)

    async def exists_by_source(self, source: str, source_listing_id: str) -> bool:
        stmt = select(OfferModel.id).where(
            OfferModel.source == OfferSource(source),
            OfferModel.source_listing_id == source_listing_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def upsert(self, offer: Offer) -> Offer:
        """Insert a new offer, or update price/availability if the source listing
        already exists (Band 07 pipeline: Deduplicate step)."""
        stmt = select(OfferModel).where(
            OfferModel.source == offer.source,
            OfferModel.source_listing_id == offer.source_listing_id,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        category_id = await self._category_id_for(offer.category)

        if existing is not None:
            existing.title = offer.title
            existing.description = offer.description
            existing.price_amount = Decimal(str(offer.price_amount))
            existing.price_currency = offer.price_currency
            existing.images = offer.images
            existing.location = offer.location
            existing.url = offer.url
            existing.is_active = True
            row = existing
        else:
            row = OfferModel(
                id=offer.id,
                source=offer.source,
                source_listing_id=offer.source_listing_id,
                title=offer.title,
                description=offer.description,
                price_amount=Decimal(str(offer.price_amount)),
                price_currency=offer.price_currency,
                category_id=category_id,
                images=offer.images,
                location=offer.location,
                url=offer.url,
                listed_at=offer.created_at,
            )
            self._session.add(row)

        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row, offer.category.value)

    async def list_by_category(
        self, category: str, *, limit: int = 20, cursor: str | None = None
    ) -> list[Offer]:
        stmt = (
            select(OfferModel, CategoryModel.code)
            .join(CategoryModel, OfferModel.category_id == CategoryModel.id)
            .where(CategoryModel.code == category, OfferModel.deleted_at.is_(None))
            .order_by(OfferModel.created_at.desc())
            .limit(limit)
        )
        if cursor:
            stmt = stmt.where(OfferModel.id > uuid.UUID(cursor))

        rows = (await self._session.execute(stmt)).all()
        return [_to_entity(row, code) for row, code in rows]
