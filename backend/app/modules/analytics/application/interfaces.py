"""Public interface of the `analytics` module."""

from __future__ import annotations

from typing import Any, Protocol

from app.modules.analytics.domain.entities import AnalyticsEvent


class AnalyticsCollectorProtocol(Protocol):
    async def track(
        self, event_name: str, *, user_id: str | None, properties: dict[str, Any]
    ) -> None: ...

    async def list_recent(self, event_name: str, *, limit: int = 100) -> list[AnalyticsEvent]: ...
