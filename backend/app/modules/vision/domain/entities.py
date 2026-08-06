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
    """Result of an actual vision-model pass over the listing images."""

    condition: str  # "excellent" | "good" | "fair" | "poor" | "damaged" | "unclear"
    confidence: float  # 0.0-1.0, the model's own confidence in this assessment
    observed_damage: list[str]  # clearly visible in the photos
    uncertain_notes: list[str]  # possible but not clearly visible/certain
    missing_components: list[str]
    reasoning: str


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
