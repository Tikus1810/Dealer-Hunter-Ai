"""Unit tests for ClaudeCosmeticConditionAnalyzer against a mocked Anthropic
API (respx) — no real network calls, no real API key needed."""

from __future__ import annotations

import json

import anthropic
import httpx
import pytest
import respx

from app.core.config import Settings
from app.modules.vision.infrastructure.claude_vision_provider import (
    ClaudeCosmeticConditionAnalyzer,
    ClaudeCosmeticConditionError,
)

MESSAGES_URL = "https://api.anthropic.com/v1/messages"


def _settings() -> Settings:
    return Settings(anthropic_api_key="test-key", anthropic_vision_model="claude-opus-5")


def _client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key="test-key")


def _assessment_response(**overrides: object) -> dict[str, object]:
    body = {
        "cosmetic_condition": "good",
        "confidence": 0.8,
        "observed_damage": ["small scuff on the lid"],
        "uncertain_notes": [],
        "missing_components": [],
        "reasoning": "Photos show light wear consistent with normal use.",
    }
    body.update(overrides)
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5",
        "content": [{"type": "text", "text": json.dumps(body)}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


def test_missing_api_key_raises_without_a_preconstructed_client() -> None:
    settings = Settings(anthropic_api_key="")
    with pytest.raises(ClaudeCosmeticConditionError, match="not configured"):
        ClaudeCosmeticConditionAnalyzer(settings)


async def test_analyze_with_no_images_raises() -> None:
    analyzer = ClaudeCosmeticConditionAnalyzer(_settings(), client=_client())
    with pytest.raises(ClaudeCosmeticConditionError, match="no images"):
        await analyzer.analyze([], category_hint="macbook")


@respx.mock
async def test_analyze_returns_parsed_assessment() -> None:
    respx.post(MESSAGES_URL).mock(return_value=httpx.Response(200, json=_assessment_response()))

    analyzer = ClaudeCosmeticConditionAnalyzer(_settings(), client=_client())
    result = await analyzer.analyze(["https://x/1.jpg", "https://x/2.jpg"], category_hint="macbook")

    assert result.condition == "good"
    assert result.confidence == 0.8
    assert result.observed_damage == ["small scuff on the lid"]
    assert result.reasoning
    # Band 16: AI Rules — every assessment records which model/prompt
    # version actually produced it, not just what's configured today.
    assert result.model_used == "claude-opus-5"
    assert result.prompt_version


@respx.mock
async def test_analyze_caps_images_at_max_per_call() -> None:
    route = respx.post(MESSAGES_URL).mock(
        return_value=httpx.Response(200, json=_assessment_response())
    )

    analyzer = ClaudeCosmeticConditionAnalyzer(_settings(), client=_client())
    urls = [f"https://x/{i}.jpg" for i in range(20)]
    await analyzer.analyze(urls, category_hint="macbook")

    sent_body = json.loads(route.calls.last.request.content)
    image_blocks = [b for b in sent_body["messages"][0]["content"] if b["type"] == "image"]
    assert len(image_blocks) == ClaudeCosmeticConditionAnalyzer._MAX_IMAGES_PER_CALL


@respx.mock
async def test_analyze_raises_on_refusal() -> None:
    respx.post(MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5",
                "content": [],
                "stop_reason": "refusal",
                "stop_sequence": None,
                "usage": {"input_tokens": 100, "output_tokens": 0},
            },
        )
    )

    analyzer = ClaudeCosmeticConditionAnalyzer(_settings(), client=_client())
    with pytest.raises(ClaudeCosmeticConditionError, match="declined"):
        await analyzer.analyze(["https://x/1.jpg"], category_hint="macbook")


@respx.mock
async def test_analyze_raises_on_http_error() -> None:
    respx.post(MESSAGES_URL).mock(
        return_value=httpx.Response(
            500, json={"type": "error", "error": {"type": "api_error", "message": "boom"}}
        )
    )

    analyzer = ClaudeCosmeticConditionAnalyzer(_settings(), client=_client())
    with pytest.raises(ClaudeCosmeticConditionError, match="API call failed"):
        await analyzer.analyze(["https://x/1.jpg"], category_hint="macbook")
