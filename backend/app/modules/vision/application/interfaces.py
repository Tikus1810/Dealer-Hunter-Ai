"""Public interface of the `vision` module (Band 02/08)."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.vision.domain.entities import VisionObservation


class VisionAnalysisServiceProtocol(Protocol):
    async def analyze(self, offer_id: uuid.UUID) -> VisionObservation:
        """Analyzes an offer's listing images. Never invents facts the
        images don't support (Band 08 scope)."""
        ...
