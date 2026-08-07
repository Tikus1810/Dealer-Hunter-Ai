"""Application entrypoint / app factory.

Wires cross-cutting concerns (CORS, correlation IDs, unified error handling,
logging) and mounts each module's presentation router. Module business
logic must never live here (Band 03: no business logic in controllers).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.bootstrap import build_scheduler
from app.core.config import get_settings
from app.core.exceptions import DomainError, ErrorResponse
from app.core.logging import configure_logging, get_logger
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY_SECONDS
from app.db.redis import get_redis
from app.db.session import session_factory
from app.modules.analytics.presentation.router import router as analytics_router
from app.modules.auth.presentation.router import router as auth_router
from app.modules.notifications.presentation.router import router as notifications_router
from app.modules.offers.presentation.router import favorites_router, offers_router
from app.modules.repair.presentation.router import router as repair_router
from app.modules.scoring.presentation.router import router as scoring_router
from app.modules.search.presentation.router import router as search_router
from app.modules.users.presentation.router import router as users_router
from app.modules.vision.presentation.router import router as vision_router

logger = get_logger(__name__)

# Swagger UI (/api/docs) and Redoc (/redoc) load their own inline
# scripts/styles plus CDN assets to render — a strict Content-Security-
# Policy would break them. /docs/oauth2-redirect is Swagger's own OAuth2
# popup target, same story. Every other response from this app is pure
# JSON (Band 14: Security-Härtung — see security_headers_middleware below).
_CSP_EXEMPT_PATHS = frozenset({"/api/docs", "/redoc", "/docs/oauth2-redirect"})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    logger.info("app_startup", env=settings.app_env)

    # Band 13: the marketplace ingestion scheduler (built in Task #5, never
    # had a call site until now) runs as an in-process background loop for
    # the lifetime of this app instance — see app/bootstrap.py for why it's
    # off unless SCHEDULER_ENABLED=true and a provider is configured, and
    # why it must only run in one replica per environment.
    scheduler = build_scheduler(settings)
    if scheduler is not None:
        scheduler.start()
        logger.info("scheduler_started", interval_seconds=settings.scheduler_interval_seconds)

    yield

    if scheduler is not None:
        await scheduler.stop()
        logger.info("scheduler_stopped")
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

    @app.middleware("http")
    async def metrics_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        # `request.scope["route"]` is only populated once routing has
        # resolved, which has happened by the time `call_next` returns —
        # using it (not `request.url.path`) keeps the label cardinality
        # bounded (`/api/v1/offers/{id}`, not one series per UUID).
        route = request.scope.get("route")
        path_template = route.path if route is not None else request.url.path
        REQUEST_COUNT.labels(request.method, path_template, response.status_code).inc()
        REQUEST_LATENCY_SECONDS.labels(request.method, path_template).observe(duration)
        return response

    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """OWASP secure-headers baseline (Band 14: Security-Härtung). This
        is a JSON API consumed by the Flutter app, not a browser-rendered
        HTML app — these mostly harden it against a browser ever being
        tricked into treating a response as something it isn't (content-
        type confusion, clickjacking of the docs pages), rather than the
        classic HTML/inline-script attack surface this service doesn't have."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=()"
        )
        if settings.is_production:
            # Only meaningful behind real TLS termination — sending this
            # over plain HTTP (true of every non-production environment
            # here) would instruct browsers to force HTTPS for a host that
            # might not have it yet, a self-inflicted outage waiting to
            # happen. No environment this app actually runs in today is
            # `production` (see docs/deployment.md "Known gaps"), so this
            # is inert until one is.
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        if request.url.path not in _CSP_EXEMPT_PATHS:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
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
        """Liveness: this process can respond at all. Deliberately checks
        nothing else — a DB/Redis blip must not make an orchestrator kill
        and restart an otherwise-healthy process (that's what /ready is
        for)."""
        return {"status": "ok"}

    @app.get("/api/v1/ready", tags=["system"])
    async def ready() -> JSONResponse:
        """Readiness: this process can actually serve requests that touch
        the database/cache. An orchestrator should stop routing traffic
        here (not restart the process) while this returns 503 — e.g. during
        a Postgres failover."""
        checks: dict[str, str] = {}
        healthy = True

        try:
            async with session_factory() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except SQLAlchemyError as exc:
            checks["database"] = f"error: {exc}"
            healthy = False

        try:
            await get_redis().ping()
            checks["redis"] = "ok"
        except RedisError as exc:
            checks["redis"] = f"error: {exc}"
            healthy = False

        return JSONResponse(
            status_code=200 if healthy else 503,
            content={"status": "ok" if healthy else "unavailable", "checks": checks},
        )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    _mount_routers(app)
    return app


def _mount_routers(app: FastAPI) -> None:
    """Mount each module's presentation router under /api/v1."""
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(offers_router)
    app.include_router(scoring_router)
    app.include_router(repair_router)
    app.include_router(vision_router)
    app.include_router(search_router)
    app.include_router(favorites_router)
    app.include_router(notifications_router)
    app.include_router(analytics_router)


app = create_app()
