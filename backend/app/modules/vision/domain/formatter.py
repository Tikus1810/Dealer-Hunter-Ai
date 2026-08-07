"""Output Formatter (Band 08 architecture module): assembles the final,
structured `VisionObservation` — the shape DealBrain/RepairBrain would
consume (Band 08: "Structured observations for DealBrain and RepairBrain").
"""

from __future__ import annotations

import uuid

from app.modules.vision.domain.confidence import MIN_IMAGES_FOR_COMPLETE_SET
from app.modules.vision.domain.entities import (
    CosmeticAssessment,
    ImageQualityObservation,
    VisionObservation,
)

OBSERVATION_VERSION = "1.0.0"
_COSMETIC_CONDITION_NOTE = (
    "Cosmetic-damage detection requires a vision model that is not yet configured; "
    "only automated image-quality checks (blur, resolution, set completeness) were performed."
)


class OutputFormatter:
    def format(
        self,
        offer_id: uuid.UUID,
        image_count: int,
        per_image: list[ImageQualityObservation],
        confidence: float,
        cosmetic: CosmeticAssessment | None = None,
    ) -> VisionObservation:
        if cosmetic is not None:
            cosmetic_condition = cosmetic.condition
            cosmetic_condition_note = cosmetic.reasoning
            missing_components = cosmetic.missing_components
            cosmetic_model_used: str | None = cosmetic.model_used
            cosmetic_prompt_version: str | None = cosmetic.prompt_version
        else:
            cosmetic_condition = "not_available"
            cosmetic_condition_note = _COSMETIC_CONDITION_NOTE
            missing_components = []
            cosmetic_model_used = None
            cosmetic_prompt_version = None

        return VisionObservation(
            offer_id=offer_id,
            image_count=image_count,
            is_image_set_incomplete=image_count < MIN_IMAGES_FOR_COMPLETE_SET,
            per_image=per_image,
            cosmetic_condition=cosmetic_condition,
            cosmetic_condition_note=cosmetic_condition_note,
            missing_components=missing_components,
            confidence=confidence,
            observation_version=OBSERVATION_VERSION,
            cosmetic_model_used=cosmetic_model_used,
            cosmetic_prompt_version=cosmetic_prompt_version,
        )
