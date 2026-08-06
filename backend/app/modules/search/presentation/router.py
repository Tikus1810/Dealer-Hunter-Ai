"""Search Profiles REST endpoints (Band 10: Search Profiles resource group).
All endpoints are user-scoped: a profile is only ever visible to, or
mutable by, the user who created it.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.presentation.dependencies import get_current_user_id
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository
from app.modules.scoring.infrastructure.repository import SqlAlchemyDealScoreRepository
from app.modules.search.application.service import SearchService
from app.modules.search.domain.entities import SearchProfile
from app.modules.search.infrastructure.repository import SqlAlchemySearchProfileRepository
from app.modules.search.presentation.schemas import (
    CreateSearchProfileRequest,
    SearchProfileResponse,
    UpdateSearchProfileRequest,
)

router = APIRouter(prefix="/api/v1/search-profiles", tags=["search-profiles"])


def get_search_service(session: AsyncSession = Depends(get_db_session)) -> SearchService:
    return SearchService(
        profiles=SqlAlchemySearchProfileRepository(session),
        offers=SqlAlchemyOfferRepository(session),
        deal_scores=SqlAlchemyDealScoreRepository(session),
    )


def _to_response(profile: SearchProfile) -> SearchProfileResponse:
    return SearchProfileResponse(
        id=profile.id,
        name=profile.name,
        category=profile.category,
        keywords=profile.keywords,
        min_price=profile.min_price,
        max_price=profile.max_price,
        min_deal_score=profile.min_deal_score,
        notify_on_match=profile.notify_on_match,
        is_active=profile.is_active,
    )


@router.post("", response_model=SearchProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_search_profile(
    body: CreateSearchProfileRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: SearchService = Depends(get_search_service),
) -> SearchProfileResponse:
    profile = await service.create_profile(
        user_id,
        name=body.name,
        category=body.category,
        keywords=body.keywords,
        min_price=body.min_price,
        max_price=body.max_price,
        min_deal_score=body.min_deal_score,
        notify_on_match=body.notify_on_match,
    )
    return _to_response(profile)


@router.get("", response_model=list[SearchProfileResponse])
async def list_my_search_profiles(
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: SearchService = Depends(get_search_service),
) -> list[SearchProfileResponse]:
    profiles = await service.list_my_profiles(user_id)
    return [_to_response(p) for p in profiles]


@router.get("/{profile_id}", response_model=SearchProfileResponse)
async def get_search_profile(
    profile_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: SearchService = Depends(get_search_service),
) -> SearchProfileResponse:
    profile = await service.get_profile(user_id, profile_id)
    return _to_response(profile)


@router.patch("/{profile_id}", response_model=SearchProfileResponse)
async def update_search_profile(
    profile_id: uuid.UUID,
    body: UpdateSearchProfileRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: SearchService = Depends(get_search_service),
) -> SearchProfileResponse:
    profile = await service.update_profile(
        user_id,
        profile_id,
        name=body.name,
        category=body.category,
        keywords=body.keywords,
        min_price=body.min_price,
        max_price=body.max_price,
        min_deal_score=body.min_deal_score,
        notify_on_match=body.notify_on_match,
        is_active=body.is_active,
    )
    return _to_response(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_search_profile(
    profile_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: SearchService = Depends(get_search_service),
) -> None:
    await service.delete_profile(user_id, profile_id)
