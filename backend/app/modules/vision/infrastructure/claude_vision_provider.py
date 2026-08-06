"""Claude Vision API integration for cosmetic-condition detection (Band 08).

Optional — only constructed when `settings.anthropic_api_key` is set (see
`get_vision_service` in the presentation router). Uses Claude's vision
capability with structured outputs (`messages.parse`) so the response is
guaranteed to match `_Assessment`'s schema rather than needing brittle
free-text parsing.

The system prompt is deliberately conservative: images-only, cosmetic (not
functional) condition, and an explicit instruction to say "unclear" rather
than guess — this is the module's one deviation from "we don't determine
this" (see `entities.py`), so it has to earn that by being honest about its
own uncertainty, same as the classical checks in `observation_engine.py`.
"""

from __future__ import annotations

from typing import Any, Literal

import anthropic
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.modules.vision.domain.entities import CosmeticAssessment

_SYSTEM_PROMPT = (
    "You assess the VISIBLE cosmetic condition of a used-electronics listing from "
    "its photos only. Report only what the images actually show — never guess about "
    "functional or internal condition, only physical/cosmetic appearance visible in "
    "the photos. If the photos are too few, too blurry, or don't show enough of the "
    "device to judge confidently, say so honestly: condition 'unclear' and a low "
    "confidence score, rather than guessing."
)

_CosmeticCondition = Literal["excellent", "good", "fair", "poor", "damaged", "unclear"]


class _Assessment(BaseModel):
    """Structured-output schema for the Claude Vision response."""

    cosmetic_condition: _CosmeticCondition
    confidence: float = Field(ge=0.0, le=1.0)
    observed_damage: list[str] = Field(
        description="Damage clearly visible in the photos, e.g. 'scratch on lid'."
    )
    uncertain_notes: list[str] = Field(
        description="Possible issues that are not clearly visible or certain from the photos."
    )
    missing_components: list[str] = Field(
        description="Accessories/parts the listing implies should be present but aren't visible."
    )
    reasoning: str = Field(description="One or two sentences explaining the assessment.")


class ClaudeCosmeticConditionError(Exception):
    """Raised when the Claude Vision call fails, is refused, or returns nothing usable."""


class ClaudeCosmeticConditionAnalyzer:
    """Implements `CosmeticConditionAnalyzerProtocol`."""

    _MAX_IMAGES_PER_CALL = 8

    def __init__(
        self, settings: Settings, *, client: anthropic.AsyncAnthropic | None = None
    ) -> None:
        if not settings.anthropic_api_key and client is None:
            raise ClaudeCosmeticConditionError(
                "ANTHROPIC_API_KEY is not configured (set it in backend/.env)"
            )
        self._client = client or anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_vision_model

    async def analyze(self, image_urls: list[str], *, category_hint: str) -> CosmeticAssessment:
        if not image_urls:
            raise ClaudeCosmeticConditionError("no images to analyze")

        # Typed `Any`: the SDK expects each element to match one of its
        # content-block TypedDicts exactly, which plain `dict[str, object]`
        # literals don't structurally satisfy in mypy's eyes even though
        # they're valid at runtime (the API validates the actual JSON).
        content: list[Any] = [
            {"type": "image", "source": {"type": "url", "url": url}}
            for url in image_urls[: self._MAX_IMAGES_PER_CALL]
        ]
        content.append(
            {
                "type": "text",
                "text": (
                    f"These are listing photos of a used {category_hint.replace('_', ' ')}. "
                    "Assess only the visible cosmetic condition."
                ),
            }
        )

        try:
            response = await self._client.messages.parse(
                model=self._model,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
                output_format=_Assessment,
            )
        except anthropic.APIError as exc:
            raise ClaudeCosmeticConditionError(f"Claude Vision API call failed: {exc}") from exc

        if response.stop_reason == "refusal":
            raise ClaudeCosmeticConditionError("Claude declined to analyze these images")

        assessment = response.parsed_output
        if assessment is None:
            raise ClaudeCosmeticConditionError("Claude response did not match the expected schema")

        return CosmeticAssessment(
            condition=assessment.cosmetic_condition,
            confidence=assessment.confidence,
            observed_damage=assessment.observed_damage,
            uncertain_notes=assessment.uncertain_notes,
            missing_components=assessment.missing_components,
            reasoning=assessment.reasoning,
        )
