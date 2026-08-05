"""Public interface of the `scoring` (DealBrain) module."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.repair.domain.entities import RepairReport
from app.modules.scoring.domain.entities import DealScoreResult


class DealScoringServiceProtocol(Protocol):
    async def score_offer(
        self, offer_id: uuid.UUID, *, repair_report: RepairReport | None = None
    ) -> DealScoreResult:
        """Deterministic for identical inputs (Band 05 scoring principle).

        `repair_report` is optional: DealBrain works standalone (Task #6)
        and folds in RepairBrain's assessment (Task #7) when the caller has
        one, without depending on the `repair` module's infrastructure.
        """
        ...


class DealScoreRepositoryProtocol(Protocol):
    async def save(self, result: DealScoreResult) -> None: ...

    async def get_latest_for_offer(self, offer_id: uuid.UUID) -> DealScoreResult | None: ...
