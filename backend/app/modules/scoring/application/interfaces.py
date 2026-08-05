"""Public interface of the `scoring` (DealBrain) module."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.scoring.domain.entities import DealScoreResult


class DealScoringServiceProtocol(Protocol):
    async def score_offer(self, offer_id: uuid.UUID) -> DealScoreResult:
        """Deterministic for identical inputs (Band 05 scoring principle)."""
        ...
