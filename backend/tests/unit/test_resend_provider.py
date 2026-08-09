"""Unit tests for ResendEmailSender against a mocked HTTP layer (respx) —
no real network calls, no real Resend API key needed."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import httpx
import pytest
import respx

from app.core.config import Settings
from app.modules.notifications.infrastructure.resend_provider import (
    EmailDeliveryError,
    ResendEmailSender,
)

RESEND_URL = "https://api.resend.com/emails"


def test_missing_config_raises_at_construction() -> None:
    settings = Settings(resend_api_key="", resend_from_email="")
    with pytest.raises(EmailDeliveryError, match="must both be set"):
        ResendEmailSender(settings)


def test_missing_from_email_alone_still_raises() -> None:
    settings = Settings(resend_api_key="re_test123", resend_from_email="")
    with pytest.raises(EmailDeliveryError, match="must both be set"):
        ResendEmailSender(settings)


@pytest.fixture
def settings() -> Settings:
    return Settings(resend_api_key="re_test123", resend_from_email="deals@example.com")


@pytest.fixture
async def sender(settings: Settings) -> AsyncGenerator[ResendEmailSender]:
    async with httpx.AsyncClient() as client:
        yield ResendEmailSender(settings, http_client=client)


@respx.mock
async def test_send_email_posts_the_expected_request(sender: ResendEmailSender) -> None:
    route = respx.post(RESEND_URL).mock(return_value=httpx.Response(200, json={"id": "email-123"}))

    await sender.send_email(to="user@example.com", subject="Neuer Deal!", body="Schau's dir an.")

    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer re_test123"
    payload = json.loads(request.content)
    assert payload["from"] == "deals@example.com"
    assert payload["to"] == ["user@example.com"]
    assert payload["subject"] == "Neuer Deal!"
    assert payload["text"] == "Schau's dir an."


@respx.mock
async def test_send_email_raises_on_error_response(sender: ResendEmailSender) -> None:
    respx.post(RESEND_URL).mock(
        return_value=httpx.Response(422, json={"message": "invalid `to` field"})
    )

    with pytest.raises(EmailDeliveryError, match="422"):
        await sender.send_email(to="not-an-email", subject="x", body="y")


@respx.mock
async def test_send_email_raises_on_network_error(sender: ResendEmailSender) -> None:
    respx.post(RESEND_URL).mock(side_effect=httpx.ConnectError("connection refused"))

    with pytest.raises(EmailDeliveryError, match="Resend request failed"):
        await sender.send_email(to="user@example.com", subject="x", body="y")
