"""Vision AI domain entities (Band 08).

`VisionObservation.cosmetic_condition` defaults to `"not_available"` with a
note explaining why, rather than a guessed value, when no cosmetic-condition
analyzer is configured (no `ANTHROPIC_API_KEY` set — see
`ClaudeCosmeticConditionAnalyzer`). Band 08: "distinguish clearly between
observed facts and uncertain inferences" applies just as much to "we don't
have this fact" as to a low-confidence one — and `CosmeticAssessment` keeps
that split explicit even once a real analyzer is wired in: `observed_damage`
is what the photos clearly show, `uncertain_notes` is everything short of that.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.ai_rules import validate_confidence


@dataclass(frozen=True, slots=True)
class ImageQualityObservation:
    image_url: str
    is_reachable: bool
    is_blurry: bool | None  # None when unreachable/undecodable
    resolution: tuple[int, int] | None
    is_low_resolution: bool | None
    note: str


@dataclass(frozen=True, slots=True)
class CosmeticAssessment:
    """Result of an actual vision-model pass over the listing images.

    `model_used`/`prompt_version` (Band 16: AI Rules — "model versioning",
    "prompt management") make every assessment traceable to exactly what
    produced it: `ANTHROPIC_VISION_MODEL` is operator-configurable, so two
    assessments of the same photos taken months apart may have run against
    different models entirely; `prompt_version` does the same for the
    system prompt (`_SYSTEM_PROMPT`/`_PROMPT_VERSION` in
    `claude_vision_provider.py`) independently of the model.
    """

    condition: str  # "excellent" | "good" | "fair" | "poor" | "damaged" | "unclear"
    confidence: float  # 0.0-1.0, the model's own confidence in this assessment
    observed_damage: list[str]  # clearly visible in the photos
    uncertain_notes: list[str]  # possible but not clearly visible/certain
    missing_components: list[str]
    reasoning: str
    model_used: str
    prompt_version: str

    def __post_init__(self) -> None:
        # Band 16: AI Rules — backstop, same reasoning as DealScoreResult's.
        validate_confidence("confidence", self.confidence)


@dataclass(frozen=True, slots=True)
class VisionObservation:
    offer_id: uuid.UUID
    image_count: int
    is_image_set_incomplete: bool
    per_image: list[ImageQualityObservation] = field(default_factory=list)
    cosmetic_condition: str = "not_available"
    cosmetic_condition_note: str = ""
    missing_components: list[str] = field(default_factory=list)
    confidence: float = 0.0
    observation_version: str = "1.0.0"
    # None when cosmetic_condition == "not_available" (no analyzer
    # configured) — there's nothing to attribute provenance to yet.
    cosmetic_model_used: str | None = None
    cosmetic_prompt_version: str | None = None

    def __post_init__(self) -> None:
        validate_confidence("confidence", self.confidence)
