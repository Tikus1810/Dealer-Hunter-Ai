"""Application entrypoint / app factory.

Wires cross-cutting concerns (CORS, correlation IDs, unified error handling,
logging) and mounts each module's presentation router. Module business
logic must never live here (Band 03: no business logic in controllers).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import DomainError, ErrorResponse
from app.core.logging import configure_logging, get_logger
from app.modules.auth.presentation.router import router as auth_router
from app.modules.repair.presentation.router import router as repair_router
from app.modules.scoring.presentation.router import router as scoring_router
from app.modules.users.presentation.router import router as users_router
from app.modules.vision.presentation.router import router as vision_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    logger.info("app_startup", env=settings.app_env)
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        body = ErrorResponse(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            correlation_id=correlation_id,
        )
        return JSONResponse(status_code=exc.http_status, content=body.model_dump())

    @app.get("/api/v1/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    _mount_routers(app)
    return app


def _mount_routers(app: FastAPI) -> None:
    """Mount each module's presentation router under /api/v1.

    Modules register their router here as soon as their presentation layer
    exists (offers/notifications land in later tasks).
    """
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(scoring_router)
    app.include_router(repair_router)
    app.include_router(vision_router)


app = create_app()
