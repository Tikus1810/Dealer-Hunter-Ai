"""Resend adapter for email notifications (Band 11) — implements
`EmailSenderProtocol`. Optional, same pattern as the FCM/eBay/Claude
Vision providers: without `settings.resend_api_key`/`resend_from_email`
configured, this raises at construction time rather than being wired in
at all (see `presentation/router.py`'s `get_notification_service`).

Calls Resend's HTTP API directly via `httpx`
(https://resend.com/docs/api-reference/emails/send-email) rather than
through Resend's own Python SDK — this project only ever needs the one
"send an email" endpoint, so adding a whole SDK dependency for a single
POST call would be disproportionate (same reasoning `EbayApiProvider`
uses for calling eBay's REST API directly).
"""

from __future__ import annotations

import httpx

from app.core.config import Settings

_API_URL = "https://api.resend.com/emails"


class EmailDeliveryError(Exception):
    """Resend rejected or failed to deliver an email (network error, 4xx/5xx
    response, malformed request). The caller may retry (Band 11: delivery
    retries) — this is not necessarily a permanently bad address."""


class ResendEmailSender:
    """Implements `EmailSenderProtocol`
    (app.modules.notifications.application.interfaces)."""

    def __init__(self, settings: Settings, *, http_client: httpx.AsyncClient | None = None) -> None:
        if not settings.resend_api_key or not settings.resend_from_email:
            raise EmailDeliveryError("RESEND_API_KEY and RESEND_FROM_EMAIL must both be set")
        self._api_key = settings.resend_api_key
        self._from_email = settings.resend_from_email
        self._client = http_client or httpx.AsyncClient(timeout=10.0)
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def send_email(self, *, to: str, subject: str, body: str) -> None:
        try:
            response = await self._client.post(
                _API_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "from": self._from_email,
                    "to": [to],
                    "subject": subject,
                    # Plain text only for now — every NotificationTemplateRenderer
                    # output (domain/templates.py) is plain text, matching PUSH's
                    # notification body. An `html` field is a natural follow-up
                    # once templates render actual HTML, not needed to make
                    # delivery work.
                    "text": body,
                },
            )
        except httpx.HTTPError as exc:
            raise EmailDeliveryError(f"Resend request failed: {exc}") from exc

        if response.status_code >= 400:
            raise EmailDeliveryError(
                f"Resend rejected the email (HTTP {response.status_code}): {response.text}"
            )
