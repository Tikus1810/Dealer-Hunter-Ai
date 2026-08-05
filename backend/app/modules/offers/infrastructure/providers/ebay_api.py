"""eBay.com / eBay.de official Browse API provider (Band 07 MarketplaceProvider).

Uses the OAuth2 client-credentials grant (application access token — no
seller/buyer login involved) and the public Browse API's item summary
search. Docs:
- Auth:   https://developer.ebay.com/api-docs/static/oauth-client-credentials-grant.html
- Browse: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search

Requires `settings.ebay_client_id` / `ebay_client_secret` (a registered
eBay developer application) — without them, `search()` raises at the token
request step rather than silently returning nothing.
"""

from __future__ import annotations

import base64
import time
import uuid
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.offers.domain.entities import OfferCategory, OfferSource, RawListing

logger = get_logger(__name__)

_CATEGORY_QUERY: dict[OfferCategory, str] = {
    OfferCategory.WINDOWS_LAPTOP: "windows laptop",
    OfferCategory.MACBOOK: "macbook",
    OfferCategory.IPHONE: "iphone",
    OfferCategory.GAME_CONSOLE: "game console",
}

_OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"


class EbayApiError(Exception):
    """Raised for non-retryable eBay API failures (auth, 4xx, malformed response)."""


class EbayApiProvider:
    """Implements `MarketplaceProviderProtocol` for source `OfferSource.EBAY`."""

    source = OfferSource.EBAY.value

    def __init__(self, settings: Settings, *, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.AsyncClient(timeout=10.0)
        self._owns_client = http_client is None
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def _api_base(self) -> str:
        return (
            "https://api.ebay.com"
            if self._settings.ebay_env.upper() == "PRODUCTION"
            else "https://api.sandbox.ebay.com"
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search(
        self, *, category: OfferCategory, query: str | None = None, limit: int = 20
    ) -> list[RawListing]:
        token = await self._get_access_token()
        effective_query = query or _CATEGORY_QUERY[category]

        response = await self._search_request(token, effective_query, limit)
        items: list[dict[str, Any]] = response.get("itemSummaries", [])

        return [
            RawListing(
                source=OfferSource.EBAY,
                source_listing_id=item["itemId"],
                category=category,
                payload=item,
            )
            for item in items
            if "itemId" in item
        ]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def _search_request(self, token: str, query: str, limit: int) -> dict[str, Any]:
        response = await self._client.get(
            f"{self._api_base}/buy/browse/v1/item_summary/search",
            params={"q": query, "limit": str(min(limit, 200))},
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE",
                "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=DE",
                "X-Correlation-ID": str(uuid.uuid4()),
            },
        )
        if response.status_code >= 500:
            raise httpx.TransportError(f"eBay Browse API returned {response.status_code}")
        if response.status_code != 200:
            raise EbayApiError(
                f"eBay Browse API search failed: {response.status_code} {response.text[:500]}"
            )
        result: dict[str, Any] = response.json()
        return result

    async def _get_access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        if not self._settings.ebay_client_id or not self._settings.ebay_client_secret:
            raise EbayApiError(
                "EBAY_CLIENT_ID / EBAY_CLIENT_SECRET are not configured "
                "(set them in backend/.env — see .env.example)"
            )

        credentials = base64.b64encode(
            f"{self._settings.ebay_client_id}:{self._settings.ebay_client_secret}".encode()
        ).decode()

        response = await self._client.post(
            f"{self._api_base}/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": _OAUTH_SCOPE},
        )
        if response.status_code != 200:
            raise EbayApiError(
                f"eBay OAuth token request failed: {response.status_code} {response.text[:500]}"
            )

        body = response.json()
        token: str = body["access_token"]
        self._token = token
        # Refresh a little early to avoid racing the real expiry.
        self._token_expires_at = time.monotonic() + int(body["expires_in"]) - 60
        return token
