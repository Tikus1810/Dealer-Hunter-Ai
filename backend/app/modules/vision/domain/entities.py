"""Vision AI domain entities (Band 08).

`VisionObservation` is deliberately explicit about what v1 does and does
not determine — `cosmetic_condition` is always `"not_available"` with a
note explaining why, rather than a guessed value, because no vision model
is configured yet (this repo's v1 scope: classical image-quality checks
only — blur, resolution, image-set completeness). Band 08: "distinguish
clearly between observed facts and uncertain inferences" applies just as
much to "we don't have this fact" as to a low-confidence one.
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
