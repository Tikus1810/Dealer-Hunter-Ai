"""Pydantic v2 DTOs for the Vision AI API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ImageQualityObservationResponse(BaseModel):
    image_url: str
    is_reachable: bool
    is_blurry: bool | None
    resolution: tuple[int, int] | None
    is_low_resolution: bool | None
    note: str


class VisionObservationResponse(BaseModel):
    offer_id: uuid.UUID
    image_count: int
    is_image_set_incomplete: bool
    per_image: list[ImageQualityObservationResponse]
    cosmetic_condition: str
    cosmetic_condition_note: str
    missing_components: list[str]
    confidence: float
    observation_version: str
