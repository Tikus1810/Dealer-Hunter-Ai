"""Auth REST endpoints (Band 10: /api/v1, Band 03: no business logic in controllers).

Handlers only translate HTTP <-> DTOs and delegate to `AuthService`; the
`get_db_session` dependency commits/rolls back the unit of work.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.modules.auth.application.service import AuthService
from app.modules.auth.infrastructure.repository import SqlAlchemyRefreshTokenRepository
from app.modules.auth.presentation.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.modules.users.infrastructure.repository import SqlAlchemyUserRepository

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        settings=settings,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
async def register(
    body: RegisterRequest, service: AuthService = Depends(get_auth_service)
) -> RegisterResponse:
    user_id = await service.register(email=body.email, password=body.password)
    return RegisterResponse(id=user_id)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    tokens = await service.login(email=body.email, password=body.password)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    tokens = await service.refresh(refresh_token=body.refresh_token)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(body: RefreshRequest, service: AuthService = Depends(get_auth_service)) -> None:
    await service.logout(refresh_token=body.refresh_token)
