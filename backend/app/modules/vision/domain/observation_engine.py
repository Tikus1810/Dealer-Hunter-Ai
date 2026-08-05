"""Observation Engine (Band 08 architecture module).

Pure computation on an already-decoded image (fetching is the Image
Preprocessor's job, in `infrastructure/`) — no I/O here, deterministic for
identical pixel data.

Blur is estimated via edge-detection variance: a sharp photo has strong,
varied edges; a blurry one has weak, uniform ones. This is a classical,
well-known heuristic (not a trained model) — see Band 08 note in
`entities.py` about what v1 does and doesn't determine.
"""

from __future__ import annotations

from PIL import Image, ImageFilter, ImageStat

from app.modules.vision.domain.entities import ImageQualityObservation

BLUR_VARIANCE_THRESHOLD = 50.0
MIN_WIDTH = 400
MIN_HEIGHT = 300
# FIND_EDGES treats out-of-bounds pixels as black, which draws a bright
# ring around the border of the *edges* image regardless of how sharp the
# photo actually is. Left uncropped, that ring alone can push even a
# perfectly flat image's variance above the threshold. Crop it out before
# measuring.
_EDGE_CROP_MARGIN = 5


class ObservationEngine:
    def assess(self, image_url: str, image: Image.Image) -> ImageQualityObservation:
        variance = self._blur_variance(image)
        is_blurry = variance < BLUR_VARIANCE_THRESHOLD

        width, height = image.size
        is_low_resolution = width < MIN_WIDTH or height < MIN_HEIGHT

        notes = []
        if is_blurry:
            notes.append(f"low edge variance ({variance:.0f}), likely blurry")
        if is_low_resolution:
            notes.append(f"resolution {width}x{height} below minimum {MIN_WIDTH}x{MIN_HEIGHT}")

        return ImageQualityObservation(
            image_url=image_url,
            is_reachable=True,
            is_blurry=is_blurry,
            resolution=(width, height),
            is_low_resolution=is_low_resolution,
            note="; ".join(notes) or "no quality issues detected",
        )

    @staticmethod
    def _blur_variance(image: Image.Image) -> float:
        grayscale = image.convert("L")
        edges = grayscale.filter(ImageFilter.FIND_EDGES)

        width, height = edges.size
        margin = min(_EDGE_CROP_MARGIN, width // 4, height // 4)
        if margin > 0:
            edges = edges.crop((margin, margin, width - margin, height - margin))

        variance = ImageStat.Stat(edges).var[0]
        return float(variance)
