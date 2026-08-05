"""Public interface of the `repair` (RepairBrain) module."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.repair.domain.entities import RepairReport


class RepairAnalysisServiceProtocol(Protocol):
    async def analyze(
        self, offer_id: uuid.UUID, *, reported_defects: list[str]
    ) -> RepairReport: ...


class RepairReportRepositoryProtocol(Protocol):
    async def save(self, report: RepairReport) -> None: ...

    async def get_latest_for_offer(self, offer_id: uuid.UUID) -> RepairReport | None: ...
