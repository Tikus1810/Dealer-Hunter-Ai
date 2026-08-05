"""SQLAlchemy models for the `offers` module (Band 09): Category, Product,
SellerScore, Offer, PriceHistory, Favorite.

Note on categories: the domain layer (`domain/entities.py`) works with the
in-memory `OfferCategory` enum; persistence normalizes categories into their
own table (`CategoryModel.code` mirrors the enum values) so the catalog can
grow without a schema migration for every new device category (Band 20:
"additional device categories" roadmap item). The offers repository
(Task #5) is responsible for translating between the two.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.offers.domain.entities import OfferSource


class CategoryModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )


class ProductModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Canonical device model (e.g. "MacBook Pro 14 M3"), used to link offers
    of the same device for price history and market-value estimation."""

    __tablename__ = "products"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    brand: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    variant: Mapped[str | None] = mapped_column(String(120))
    specs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("brand", "model", "variant", name="uq_products_brand_model_variant"),
    )


class SellerScoreModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "seller_scores"

    source: Mapped[OfferSource] = mapped_column(
        Enum(OfferSource, native_enum=False, length=32, validate_strings=True), nullable=False
    )
    source_seller_id: Mapped[str] = mapped_column(String(120), nullable=False)
    seller_name: Mapped[str | None] = mapped_column(String(120))
    rating_avg: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(default=0, nullable=False)
    trust_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    __table_args__ = (
        UniqueConstraint("source", "source_seller_id", name="uq_seller_scores_source_seller"),
    )


class OfferModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "offers"

    source: Mapped[OfferSource] = mapped_column(
        Enum(OfferSource, native_enum=False, length=32, validate_strings=True),
        nullable=False,
        index=True,
    )
    source_listing_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    seller_score_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_scores.id", ondelete="SET NULL")
    )
    images: Mapped[list[str]] = mapped_column(ARRAY(String(500)), default=list, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "source_listing_id", name="uq_offers_source_listing"),
        Index("ix_offers_category_price", "category_id", "price_amount"),
    )


class PriceHistoryModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "price_history"

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    offer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), index=True
    )
    price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class FavoriteModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "offer_id", name="uq_favorites_user_offer"),)
