"""Confidence Estimator (Band 08 architecture module).

Confidence reflects how much we can trust the image-quality read overall —
not the (not-yet-available) cosmetic assessment. Zero images or zero
reachable images means zero confidence; an incomplete set discounts an
otherwise-good read (Band 08 functional requirement: "Flag incomplete
image sets").
"""

from __future__ import annotations

from app.modules.vision.domain.entities import ImageQualityObservation

MIN_IMAGES_FOR_COMPLETE_SET = 3
INCOMPLETE_SET_CONFIDENCE_PENALTY = 0.7  # multiplier, not subtraction


class ConfidenceEstimator:
    def estimate(self, per_image: list[ImageQualityObservation]) -> float:
        if not per_image:
            return 0.0

        reachable = [obs for obs in per_image if obs.is_reachable]
        if not reachable:
            return 0.0

        good = [
            obs for obs in reachable if obs.is_blurry is False and obs.is_low_resolution is False
        ]
        confidence = len(good) / len(per_image)

        if len(per_image) < MIN_IMAGES_FOR_COMPLETE_SET:
            confidence *= INCOMPLETE_SET_CONFIDENCE_PENALTY

        return round(min(1.0, confidence), 2)
