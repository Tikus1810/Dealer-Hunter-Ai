"""eBay Kleinanzeigen provider (Band 07 MarketplaceProvider).

IMPORTANT — legal/ToS note (flagged to the project owner, see README):
Kleinanzeigen has no official public API, and its Terms of Service prohibit
automated data collection. This provider therefore:

  - is OFF by default (`settings.kleinanzeigen_provider_enabled = False`);
    `search()` refuses to run at all unless it is explicitly enabled.
  - checks `robots.txt` before every request and refuses disallowed paths.
  - only ever requests plain, unfiltered search-result and listing pages —
    the filtered URL variants (radius, sort order, price range, seller
    type, shipping) that robots.txt disallows are never used.
  - rate-limits itself (`settings.kleinanzeigen_request_delay_seconds`
    between requests) and identifies itself honestly via `User-Agent`
    rather than impersonating a browser.
  - never attempts to solve CAPTCHAs or otherwise bypass bot detection —
    if the site blocks it, it fails loudly instead of working around that.

Get legal sign-off before enabling this in production.

CSS selectors below were confirmed against the live search results page and
one listing detail page (a repair-service ad, not a device listing) on
2026-08-05. Kleinanzeigen's markup can change; re-verify before relying on
this in production, and expect to maintain it like any scraper.
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import quote, urljoin
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.offers.domain.entities import OfferCategory, OfferSource, RawListing

logger = get_logger(__name__)

_BASE_URL = "https://www.kleinanzeigen.de"
_USER_AGENT = "DealHunterAI-Bot/1.0 (research/ingestion; contact via project owner)"

# Verified real subcategory ("Laptops & Notebooks") for the two laptop
# categories. iPhone / game consoles fall back to an unscoped, all-category
# search (`k0`, confirmed valid via the site's own "Alle Kategorien" link) —
# their precise category ids were not verified and should not be guessed.
_CATEGORY_PATH_SUFFIX: dict[OfferCategory, str] = {
    OfferCategory.WINDOWS_LAPTOP: "k0c278",
    OfferCategory.MACBOOK: "k0c278",
}
_CATEGORY_QUERY: dict[OfferCategory, str] = {
    OfferCategory.WINDOWS_LAPTOP: "windows laptop",
    OfferCategory.MACBOOK: "macbook",
    OfferCategory.IPHONE: "iphone",
    OfferCategory.GAME_CONSOLE: "spielekonsole",
}


class KleinanzeigenDisabledError(Exception):
    """Raised when `search()` is called without the provider being enabled."""


class RobotsDisallowedError(Exception):
    """Raised when robots.txt disallows the path this provider would fetch."""


class KleinanzeigenProvider:
    """Implements `MarketplaceProviderProtocol` for source `OfferSource.EBAY_KLEINANZEIGEN`.

    Deliberately fetches only the search-results page per call (not a
    detail page per listing) to keep the request footprint minimal; see
    `fetch_raw()` for optional, separately-invoked detail enrichment.
    """

    source = OfferSource.EBAY_KLEINANZEIGEN.value

    def __init__(self, settings: Settings, *, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.AsyncClient(
            timeout=10.0, headers={"User-Agent": _USER_AGENT}
        )
        self._owns_client = http_client is None
        self._robots: RobotFileParser | None = None
        self._last_request_at: float = 0.0

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search(
        self, *, category: OfferCategory, query: str | None = None, limit: int = 20
    ) -> list[RawListing]:
        if not self._settings.kleinanzeigen_provider_enabled:
            raise KleinanzeigenDisabledError(
                "Kleinanzeigen provider is disabled (KLEINANZEIGEN_PROVIDER_ENABLED=false). "
                "See the ToS note in this module's docstring before enabling it."
            )

        url = self._build_search_url(category=category, query=query)
        html = await self._get(url)
        return self._parse_search_results(html, category=category, limit=limit)

    async def fetch_raw(self, listing_ref: str, *, category: OfferCategory) -> RawListing:
        """Optional enrichment: fetches one listing's detail page. Not called
        by `search()` — invoke explicitly if a caller needs the full
        description or seller name beyond what the search card provides."""
        if not self._settings.kleinanzeigen_provider_enabled:
            raise KleinanzeigenDisabledError(
                "Kleinanzeigen provider is disabled (KLEINANZEIGEN_PROVIDER_ENABLED=false)."
            )
        url = urljoin(_BASE_URL, listing_ref)
        html = await self._get(url)
        return self._parse_detail_page(html, url=url, category=category)

    # -- URL building -----------------------------------------------------

    def _build_search_url(self, *, category: OfferCategory, query: str | None) -> str:
        effective_query = query or _CATEGORY_QUERY[category]
        slug = quote(effective_query.strip().lower().replace(" ", "-"))
        suffix = _CATEGORY_PATH_SUFFIX.get(category, "k0")
        return f"{_BASE_URL}/s-{slug}/{suffix}"

    # -- HTML parsing -------------------------------------------------------

    def _parse_search_results(
        self, html: str, *, category: OfferCategory, limit: int
    ) -> list[RawListing]:
        soup = BeautifulSoup(html, "lxml")
        articles = soup.select("#srchrslt-adtable article.aditem")[:limit]

        listings: list[RawListing] = []
        for article in articles:
            listing_id = article.get("data-adid")
            href = article.get("data-href")
            if not listing_id or not href:
                continue

            title_el = article.select_one("h2.text-module-begin a.ellipsis")
            price_el = article.select_one(".aditem-main--middle--price-shipping--price")
            desc_el = article.select_one(".aditem-main--middle--description")
            location_el = article.select_one(".aditem-main--top--left")
            image_el = article.select_one(".aditem-image img")

            price_text = price_el.get_text(strip=True) if price_el else ""
            payload = {
                "title": title_el.get_text(strip=True) if title_el else "",
                "price_amount": self._parse_price(price_text),
                "description": desc_el.get_text(strip=True) if desc_el else "",
                "location": location_el.get_text(strip=True) if location_el else None,
                "images": [image_el["src"]] if image_el and image_el.get("src") else [],
                "url": urljoin(_BASE_URL, str(href)),
                "seller_name": None,
            }
            listings.append(
                RawListing(
                    source=OfferSource.EBAY_KLEINANZEIGEN,
                    source_listing_id=str(listing_id),
                    category=category,
                    payload=payload,
                )
            )
        return listings

    def _parse_detail_page(self, html: str, *, url: str, category: OfferCategory) -> RawListing:
        soup = BeautifulSoup(html, "lxml")
        title_el = soup.select_one("#viewad-title")
        price_el = soup.select_one("#viewad-price")
        desc_el = soup.select_one("#viewad-description-text")
        location_el = soup.select_one("#viewad-locality")
        seller_el = soup.select_one(".userprofile-vip span")
        main_img_el = soup.select_one("#viewad-image")

        listing_id = url.rstrip("/").rsplit("-", 1)[-1]
        payload = {
            "title": title_el.get_text(strip=True) if title_el else "",
            "price_amount": self._parse_price(price_el.get_text(strip=True) if price_el else ""),
            "description": desc_el.get_text(strip=True) if desc_el else "",
            "location": location_el.get_text(strip=True) if location_el else None,
            "images": [main_img_el["src"]] if main_img_el and main_img_el.get("src") else [],
            "url": url,
            "seller_name": seller_el.get_text(strip=True) if seller_el else None,
        }
        return RawListing(
            source=OfferSource.EBAY_KLEINANZEIGEN,
            source_listing_id=listing_id,
            category=category,
            payload=payload,
        )

    @staticmethod
    def _parse_price(text: str) -> float:
        """ "1.234 €" -> 1234.0; "VB" / "Zu verschenken" / "" -> 0.0 (caller's
        validator rejects non-positive prices, which is correct here: a
        negotiable/free listing without a firm number is not a comparable deal)."""
        digits = "".join(ch for ch in text if ch.isdigit())
        return float(digits) if digits else 0.0

    # -- Networking (robots.txt + rate limit + retry) ------------------------

    async def _get(self, url: str) -> str:
        await self._ensure_allowed(url)
        await self._throttle()
        return await self._get_with_retry(url)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def _get_with_retry(self, url: str) -> str:
        response = await self._client.get(url)
        if response.status_code >= 500:
            raise httpx.TransportError(f"Kleinanzeigen returned {response.status_code} for {url}")
        response.raise_for_status()
        return response.text

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        delay = self._settings.kleinanzeigen_request_delay_seconds
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request_at = time.monotonic()

    async def _ensure_allowed(self, url: str) -> None:
        robots = await self._get_robots()
        if not robots.can_fetch(_USER_AGENT, url):
            raise RobotsDisallowedError(f"robots.txt disallows fetching {url}")

    async def _get_robots(self) -> RobotFileParser:
        if self._robots is not None:
            return self._robots
        response = await self._client.get(f"{_BASE_URL}/robots.txt")
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        self._robots = parser
        return parser
