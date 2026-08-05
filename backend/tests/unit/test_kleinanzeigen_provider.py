"""Unit tests for KleinanzeigenProvider against a mocked HTTP layer (respx).

No real requests to kleinanzeigen.de are made. The HTML fixture below
mirrors the real markup structure confirmed by manual inspection of the
live search results page (see the module docstring in
`app/modules/offers/infrastructure/providers/kleinanzeigen.py`).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx

from app.core.config import Settings
from app.modules.offers.domain.entities import OfferCategory, OfferSource
from app.modules.offers.infrastructure.providers.kleinanzeigen import (
    KleinanzeigenDisabledError,
    KleinanzeigenProvider,
    RobotsDisallowedError,
)

ROBOTS_URL = "https://www.kleinanzeigen.de/robots.txt"
PERMISSIVE_ROBOTS_TXT = "User-agent: *\nDisallow: /ad/\nDisallow: /m-einloggen.html\n"
RESTRICTIVE_ROBOTS_TXT = "User-agent: *\nDisallow: /\n"

SEARCH_RESULTS_HTML = """
<div id="srchrslt-adtable" class="itemlist ad-list it3">
  <article class="aditem" data-adid="111" data-href="/s-anzeige/macbook-air-m1/111-226-1">
    <div class="aditem-image">
      <a href="/s-anzeige/macbook-air-m1/111-226-1">
        <div class="imagebox srpimagebox">
          <img src="https://img.kleinanzeigen.de/img111.jpg" alt="MacBook Air M1">
        </div>
      </a>
    </div>
    <div class="aditem-main">
      <div class="aditem-main--top">
        <div class="aditem-main--top--left">
          <i class="icon icon-small icon-pin-gray" aria-hidden="true"></i> 10827 Berlin - Schöneberg
        </div>
      </div>
      <div class="aditem-main--middle">
        <div class="aditem-main--middle--price-shipping">
          <p class="aditem-main--middle--price-shipping--price">650 €</p>
        </div>
        <h2 class="text-module-begin">
          <a class="ellipsis"
             href="/s-anzeige/macbook-air-m1/111-226-1">MacBook Air M1 2020, 8GB/256GB</a>
        </h2>
        <p class="aditem-main--middle--description">Kaum Gebrauchsspuren, Akku bei 92%.</p>
      </div>
    </div>
  </article>
  <article class="aditem" data-adid="222" data-href="/s-anzeige/macbook-pro-defekt/222-226-2">
    <div class="aditem-image"></div>
    <div class="aditem-main">
      <div class="aditem-main--top">
        <div class="aditem-main--top--left">80331 München</div>
      </div>
      <div class="aditem-main--middle">
        <div class="aditem-main--middle--price-shipping">
          <p class="aditem-main--middle--price-shipping--price">VB</p>
        </div>
        <h2 class="text-module-begin">
          <a class="ellipsis"
             href="/s-anzeige/macbook-pro-defekt/222-226-2"
             >MacBook Pro defekt, Ersatzteilspender</a>
        </h2>
        <p class="aditem-main--middle--description">Display defekt, sonst funktionsfähig.</p>
      </div>
    </div>
  </article>
</div>
"""


@pytest.fixture
def enabled_settings() -> Settings:
    return Settings(kleinanzeigen_provider_enabled=True, kleinanzeigen_request_delay_seconds=0.0)


@pytest.fixture
async def provider(enabled_settings: Settings) -> AsyncGenerator[KleinanzeigenProvider]:
    async with httpx.AsyncClient() as client:
        yield KleinanzeigenProvider(enabled_settings, http_client=client)


async def test_search_disabled_by_default_raises() -> None:
    settings = Settings()  # kleinanzeigen_provider_enabled defaults to False
    async with httpx.AsyncClient() as client:
        provider = KleinanzeigenProvider(settings, http_client=client)
        with pytest.raises(KleinanzeigenDisabledError):
            await provider.search(category=OfferCategory.MACBOOK)


@respx.mock
async def test_search_parses_listing_cards_when_enabled(provider: KleinanzeigenProvider) -> None:
    respx.get(ROBOTS_URL).mock(return_value=httpx.Response(200, text=PERMISSIVE_ROBOTS_TXT))
    respx.get(url__startswith="https://www.kleinanzeigen.de/s-macbook/").mock(
        return_value=httpx.Response(200, text=SEARCH_RESULTS_HTML)
    )

    results = await provider.search(category=OfferCategory.MACBOOK)

    assert len(results) == 2
    first = results[0]
    assert first.source is OfferSource.EBAY_KLEINANZEIGEN
    assert first.source_listing_id == "111"
    assert first.payload["title"] == "MacBook Air M1 2020, 8GB/256GB"
    assert first.payload["price_amount"] == 650.0
    assert first.payload["location"] == "10827 Berlin - Schöneberg"
    assert first.payload["url"].endswith("/s-anzeige/macbook-air-m1/111-226-1")
    assert first.payload["images"] == ["https://img.kleinanzeigen.de/img111.jpg"]

    second = results[1]
    assert second.payload["price_amount"] == 0.0  # "VB" has no firm number


@respx.mock
async def test_search_respects_limit(provider: KleinanzeigenProvider) -> None:
    respx.get(ROBOTS_URL).mock(return_value=httpx.Response(200, text=PERMISSIVE_ROBOTS_TXT))
    respx.get(url__startswith="https://www.kleinanzeigen.de/s-macbook/").mock(
        return_value=httpx.Response(200, text=SEARCH_RESULTS_HTML)
    )

    results = await provider.search(category=OfferCategory.MACBOOK, limit=1)

    assert len(results) == 1


@respx.mock
async def test_search_honors_robots_txt_disallow(provider: KleinanzeigenProvider) -> None:
    respx.get(ROBOTS_URL).mock(return_value=httpx.Response(200, text=RESTRICTIVE_ROBOTS_TXT))

    with pytest.raises(RobotsDisallowedError):
        await provider.search(category=OfferCategory.MACBOOK)


@respx.mock
async def test_uses_scoped_laptop_category_path_for_macbook(
    provider: KleinanzeigenProvider,
) -> None:
    respx.get(ROBOTS_URL).mock(return_value=httpx.Response(200, text=PERMISSIVE_ROBOTS_TXT))
    route = respx.get(url__startswith="https://www.kleinanzeigen.de/s-macbook/").mock(
        return_value=httpx.Response(200, text="<div id='srchrslt-adtable'></div>")
    )

    await provider.search(category=OfferCategory.MACBOOK)

    assert route.called
    assert str(route.calls.last.request.url).endswith("/s-macbook/k0c278")
