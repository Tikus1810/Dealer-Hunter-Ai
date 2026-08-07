"""Offers + Favorites REST endpoints (Band 10: "Offers" and "Favorites"
resource groups, /api/v1). Offer browsing stays unauthenticated, matching
DealBrain/RepairBrain/Vision's read endpoints; Favorites are user-scoped
and require auth.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.analytics.application.service import AnalyticsService
from app.modules.analytics.infrastructure.repository import SqlAlchemyAnalyticsEventRepository
from app.modules.auth.presentation.dependencies import get_current_user_id
from app.modules.offers.application.favorite_service import FavoriteService
from app.modules.offers.application.service import OfferService
from app.modules.offers.domain.entities import Favorite, Offer
from app.modules.offers.infrastructure.favorite_repository import SqlAlchemyFavoriteRepository
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository
from app.modules.offers.presentation.schemas import (
    FavoriteListResponse,
    FavoriteResponse,
    OfferListResponse,
    OfferResponse,
)

offers_router = APIRouter(prefix="/api/v1/offers", tags=["offers"])
favorites_router = APIRouter(prefix="/api/v1/favorites", tags=["favorites"])


def get_offer_service(session: AsyncSession = Depends(get_db_session)) -> OfferService:
    return OfferService(offers=SqlAlchemyOfferRepository(session))


def get_favorite_service(session: AsyncSession = Depends(get_db_session)) -> FavoriteService:
    return FavoriteService(
        favorites=SqlAlchemyFavoriteRepository(session),
        offers=SqlAlchemyOfferRepository(session),
        analytics=AnalyticsService(SqlAlchemyAnalyticsEventRepository(session)),
    )


def _offer_to_response(offer: Offer) -> OfferResponse:
    return OfferResponse(
        id=offer.id,
        source=offer.source.value,
        source_listing_id=offer.source_listing_id,
        title=offer.title,
        description=offer.description,
        price_amount=offer.price_amount,
        price_currency=offer.price_currency,
        category=offer.category.value,
        images=offer.images,
        location=offer.location,
        url=offer.url,
        created_at=offer.created_at,
        fetched_at=offer.fetched_at,
    )


def _favorite_to_response(favorite: Favorite) -> FavoriteResponse:
    return FavoriteResponse(
        id=favorite.id, offer_id=favorite.offer_id, created_at=favorite.created_at
    )


@offers_router.get("", response_model=OfferListResponse)
async def list_offers(
    category: str = Query(..., description="Offer category code, e.g. 'macbook'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: OfferService = Depends(get_offer_service),
) -> OfferListResponse:
    offers, total = await service.list_offers(category=category, page=page, page_size=page_size)
    return OfferListResponse(
        items=[_offer_to_response(o) for o in offers], total=total, page=page, page_size=page_size
    )


@offers_router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: uuid.UUID, service: OfferService = Depends(get_offer_service)
) -> OfferResponse:
    offer = await service.get_offer(offer_id)
    return _offer_to_response(offer)


@offers_router.post(
    "/{offer_id}/favorite", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED
)
async def add_favorite(
    offer_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteResponse:
    favorite = await service.add_favorite(user_id, offer_id)
    return _favorite_to_response(favorite)


@offers_router.delete(
    "/{offer_id}/favorite", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def remove_favorite(
    offer_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: FavoriteService = Depends(get_favorite_service),
) -> None:
    await service.remove_favorite(user_id, offer_id)


@favorites_router.get("", response_model=FavoriteListResponse)
async def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteListResponse:
    favorites, total = await service.list_favorites(user_id, page=page, page_size=page_size)
    return FavoriteListResponse(
        items=[_favorite_to_response(f) for f in favorites],
        total=total,
        page=page,
        page_size=page_size,
    )
