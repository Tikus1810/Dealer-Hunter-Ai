"""Public interface of the `analytics` module."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Protocol

from app.modules.analytics.domain.entities import AnalyticsEvent


class AnalyticsCollectorProtocol(Protocol):
    """The cross-module extension point — other modules depend on this
    (never on `application.service.AnalyticsService` or anything in
    `infrastructure/`, per Band 2's module-boundary rule) to emit an event
    without knowing anything about how/where it's stored. Mirrors how
    `notifications` exposes `NotificationServiceProtocol` and `offers`
    exposes `OfferPersistedHookProtocol` for the same purpose.
    """

    async def track(
        self, event_name: str, *, user_id: uuid.UUID | None, properties: dict[str, Any]
    ) -> None: ...


class AnalyticsEventRepositoryProtocol(Protocol):
    async def create(self, event: AnalyticsEvent) -> AnalyticsEvent: ...

    async def list_recent(self, name: str, *, limit: int = 100) -> list[AnalyticsEvent]: ...

    async def count_by_name(self, name: str, *, since: datetime | None = None) -> int: ...

    async def count_distinct_users(self, name: str, *, since: datetime | None = None) -> int: ...

    async def purge_older_than(self, cutoff: datetime) -> int:
        """Deletes events with `occurred_at < cutoff`, returns how many.
        Band 15: retention — see `AnalyticsService.purge_events_older_than`
        and `scripts/purge_analytics_events.py`."""
        ...
