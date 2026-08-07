"""Auth REST endpoints (Band 10: /api/v1, Band 03: no business logic in controllers).

Handlers only translate HTTP <-> DTOs and delegate to `AuthService`; the
`get_db_session` dependency commits/rolls back the unit of work.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limit
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

# Band 14: Security-Härtung — brute-force/credential-stuffing protection
# (OWASP API4:2023). Limits are per-client-IP, deliberately asymmetric:
# login is the actual credential-guessing target (tighter window+count);
# register is cheaper to abuse for account-creation spam but each attempt
# is far more expensive for an attacker than a login guess (creates a real
# row); refresh is legitimate client behavior (silent token renewal) that
# just needs a ceiling, not a strict gate. All three are no-ops unless
# RATE_LIMIT_ENABLED=true (see app/core/rate_limit.py's module docstring).
_login_rate_limit = rate_limit("login", limit=10, window_seconds=60)
_register_rate_limit = rate_limit("register", limit=5, window_seconds=3600)
_refresh_rate_limit = rate_limit("refresh", limit=30, window_seconds=60)


def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        settings=settings,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    dependencies=[Depends(_register_rate_limit)],
)
async def register(
    body: RegisterRequest, service: AuthService = Depends(get_auth_service)
) -> RegisterResponse:
    user_id = await service.register(email=body.email, password=body.password)
    return RegisterResponse(id=user_id)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(_login_rate_limit)])
async def login(
    body: LoginRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    tokens = await service.login(email=body.email, password=body.password)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(_refresh_rate_limit)])
async def refresh(
    body: RefreshRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    tokens = await service.refresh(refresh_token=body.refresh_token)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(body: RefreshRequest, service: AuthService = Depends(get_auth_service)) -> None:
    await service.logout(refresh_token=body.refresh_token)
