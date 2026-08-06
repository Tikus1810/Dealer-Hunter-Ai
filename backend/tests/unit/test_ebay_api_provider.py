"""Unit tests for EbayApiProvider against a mocked HTTP layer (respx) — no
real network calls, no real eBay credentials needed."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx

from app.core.config import Settings
from app.modules.offers.domain.entities import OfferCategory, OfferSource
from app.modules.offers.infrastructure.providers.ebay_api import EbayApiError, EbayApiProvider

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ebay_client_id="test-id", ebay_client_secret="test-secret", ebay_env="PRODUCTION"
    )


@pytest.fixture
async def provider(settings: Settings) -> AsyncGenerator[EbayApiProvider]:
    async with httpx.AsyncClient() as client:
        yield EbayApiProvider(settings, http_client=client)


@respx.mock
async def test_search_returns_raw_listings_for_each_item_summary(provider: EbayApiProvider) -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-1", "expires_in": 7200})
    )
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {"itemId": "v1|1|0", "title": "MacBook Air M1"},
                    {"itemId": "v1|2|0", "title": "MacBook Pro M3"},
                ]
            },
        )
    )

    results = await provider.search(category=OfferCategory.MACBOOK, limit=10)

    assert len(results) == 2
    assert results[0].source is OfferSource.EBAY
    assert results[0].source_listing_id == "v1|1|0"
    assert results[0].category is OfferCategory.MACBOOK
    assert results[0].payload["title"] == "MacBook Air M1"


@respx.mock
async def test_search_uses_category_default_query_when_none_given(
    provider: EbayApiProvider,
) -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-1", "expires_in": 7200})
    )
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"itemSummaries": []}))

    await provider.search(category=OfferCategory.IPHONE)

    assert route.called
    assert route.calls.last.request.url.params["q"] == "iphone"


@respx.mock
async def test_search_reuses_cached_token_across_calls(provider: EbayApiProvider) -> None:
    token_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-1", "expires_in": 7200})
    )
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"itemSummaries": []}))

    await provider.search(category=OfferCategory.MACBOOK)
    await provider.search(category=OfferCategory.MACBOOK)

    assert token_route.call_count == 1  # second search reused the cached token


@respx.mock
async def test_search_raises_on_4xx_without_retrying(provider: EbayApiProvider) -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-1", "expires_in": 7200})
    )
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(400, text="bad request"))

    with pytest.raises(EbayApiError):
        await provider.search(category=OfferCategory.MACBOOK)

    assert route.call_count == 1  # 4xx is not retried


async def test_search_without_credentials_raises_clear_error() -> None:
    settings = Settings(ebay_client_id="", ebay_client_secret="")
    async with httpx.AsyncClient() as client:
        provider = EbayApiProvider(settings, http_client=client)
        with pytest.raises(EbayApiError, match="not configured"):
            await provider.search(category=OfferCategory.MACBOOK)
