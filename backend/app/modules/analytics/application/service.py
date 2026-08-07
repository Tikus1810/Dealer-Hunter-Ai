"""Analytics application service — implements `AnalyticsCollectorProtocol`
(Band 15). `track()` is the single write path every event goes through,
whether it came from `POST /api/v1/analytics/events` (client-driven, e.g.
Flutter screen views) or a first-party hook inside another module's
service (see AuthService/FavoriteService) — validation and the privacy
denylist apply equally to both, there is no "trusted" caller.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.exceptions import ValidationError
from app.modules.analytics.application.interfaces import AnalyticsEventRepositoryProtocol
from app.modules.analytics.domain.entities import AnalyticsEvent, AnalyticsSummary
from app.modules.analytics.domain.taxonomy import (
    DENYLISTED_PROPERTY_KEYS,
    MAX_EVENT_NAME_LENGTH,
    MAX_PROPERTY_COUNT,
    MAX_PROPERTY_KEY_LENGTH,
    MAX_PROPERTY_STRING_VALUE_LENGTH,
    is_valid_event_name,
)


class AnalyticsService:
    """Implements `AnalyticsCollectorProtocol`
    (app.modules.analytics.application.interfaces)."""

    def __init__(self, events: AnalyticsEventRepositoryProtocol) -> None:
        self._events = events

    async def track(
        self, event_name: str, *, user_id: uuid.UUID | None, properties: dict[str, Any]
    ) -> None:
        _validate_event_name(event_name)
        _validate_properties(properties)
        event = AnalyticsEvent(
            id=uuid.uuid4(), name=event_name, user_id=user_id, properties=properties
        )
        await self._events.create(event)

    async def list_recent(self, event_name: str, *, limit: int = 100) -> list[AnalyticsEvent]:
        _validate_event_name(event_name)
        return await self._events.list_recent(event_name, limit=limit)

    async def summary(self, event_name: str, *, since_days: int | None = None) -> AnalyticsSummary:
        _validate_event_name(event_name)
        since = datetime.now(UTC) - timedelta(days=since_days) if since_days is not None else None
        count = await self._events.count_by_name(event_name, since=since)
        distinct_users = await self._events.count_distinct_users(event_name, since=since)
        return AnalyticsSummary(
            event_name=event_name, count=count, distinct_users=distinct_users, since=since
        )

    async def purge_events_older_than(self, days: int) -> int:
        """Band 15: retention. Called from `scripts/purge_analytics_events.py`,
        not from any request path — deleting analytics history is an
        operational task, not something an API caller triggers."""
        if days <= 0:
            raise ValidationError(f"days must be positive, got {days}")
        cutoff = datetime.now(UTC) - timedelta(days=days)
        return await self._events.purge_older_than(cutoff)


def _validate_event_name(event_name: str) -> None:
    if len(event_name) > MAX_EVENT_NAME_LENGTH:
        raise ValidationError(
            f"event_name exceeds {MAX_EVENT_NAME_LENGTH} characters",
            details={"event_name": event_name},
        )
    if not is_valid_event_name(event_name):
        raise ValidationError(
            "event_name must be lowercase snake_case (e.g. 'offer_viewed')",
            details={"event_name": event_name},
        )


def _validate_properties(properties: dict[str, Any]) -> None:
    if len(properties) > MAX_PROPERTY_COUNT:
        raise ValidationError(
            f"more than {MAX_PROPERTY_COUNT} properties on one event",
            details={"property_count": len(properties)},
        )
    for key, value in properties.items():
        if len(key) > MAX_PROPERTY_KEY_LENGTH:
            raise ValidationError(
                f"property key exceeds {MAX_PROPERTY_KEY_LENGTH} characters",
                details={"key": key},
            )
        if key.lower() in DENYLISTED_PROPERTY_KEYS:
            # Band 15: privacy — refuse rather than silently strip, so the
            # caller (client code or a first-party hook) finds out
            # immediately instead of assuming the field was recorded.
            raise ValidationError(
                f"property key '{key}' looks like it may contain sensitive "
                "data and is not allowed on analytics events",
                details={"key": key},
            )
        if isinstance(value, str) and len(value) > MAX_PROPERTY_STRING_VALUE_LENGTH:
            raise ValidationError(
                f"property '{key}' exceeds {MAX_PROPERTY_STRING_VALUE_LENGTH} characters",
                details={"key": key},
            )
