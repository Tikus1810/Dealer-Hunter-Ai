"""Users REST endpoints (Band 10)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.presentation.dependencies import get_current_user_id
from app.modules.users.application.service import UserService
from app.modules.users.domain.entities import User
from app.modules.users.infrastructure.repository import SqlAlchemyUserRepository
from app.modules.users.presentation.schemas import UpdateProfileRequest, UserProfileResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    return UserService(users=SqlAlchemyUserRepository(session))


def _to_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=user.roles,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    return _to_response(await service.get_profile(user_id))


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    body: UpdateProfileRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    updated = await service.update_profile(user_id, display_name=body.display_name)
    return _to_response(updated)
