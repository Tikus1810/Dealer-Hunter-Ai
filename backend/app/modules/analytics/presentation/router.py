"""Analytics REST endpoints (Band 15). All endpoints require auth — there
is no anonymous event ingestion in v1 (a logged-out screen view has
nowhere useful to attribute to yet, and an open POST endpoint with no
caller identity is an abuse magnet). `GET /summary` is deliberately not
admin-only: no RBAC surface exists in this codebase yet (see
docs/security.md's "Known gaps") — any authenticated user can see
aggregate, non-personal counts for now.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.analytics.application.service import AnalyticsService
from app.modules.analytics.infrastructure.repository import SqlAlchemyAnalyticsEventRepository
from app.modules.analytics.presentation.schemas import (
    AnalyticsEventResponse,
    AnalyticsSummaryResponse,
    TrackEventRequest,
)
from app.modules.auth.presentation.dependencies import get_current_user_id

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def get_analytics_service(session: AsyncSession = Depends(get_db_session)) -> AnalyticsService:
    return AnalyticsService(SqlAlchemyAnalyticsEventRepository(session))


@router.post("/events", status_code=status.HTTP_201_CREATED, response_model=None)
async def track_event(
    body: TrackEventRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> None:
    # user_id always comes from the token, never the request body — a
    # client cannot attribute an event to a different user.
    await service.track(body.event_name, user_id=user_id, properties=body.properties)


@router.get("/events/{event_name}", response_model=list[AnalyticsEventResponse])
async def list_recent_events(
    event_name: str,
    limit: int = Query(default=100, ge=1, le=500),
    _user_id: uuid.UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[AnalyticsEventResponse]:
    events = await service.list_recent(event_name, limit=limit)
    return [
        AnalyticsEventResponse(
            id=e.id,
            name=e.name,
            user_id=e.user_id,
            properties=e.properties,
            occurred_at=e.occurred_at,
        )
        for e in events
    ]


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_summary(
    event_name: str,
    since_days: int | None = Query(default=None, ge=1),
    _user_id: uuid.UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsSummaryResponse:
    summary = await service.summary(event_name, since_days=since_days)
    return AnalyticsSummaryResponse(
        event_name=summary.event_name,
        count=summary.count,
        distinct_users=summary.distinct_users,
        since=summary.since,
    )
