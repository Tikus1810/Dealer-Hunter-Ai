"""Public interface of the `offers` module, including the Band 07 Marketplace
Engine's core interfaces: MarketplaceProvider, SearchProvider, OfferFetcher,
OfferNormalizer, OfferValidator, OfferRepository, SearchScheduler.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.offers.domain.entities import Offer, OfferCategory, RawListing


class OfferRepositoryProtocol(Protocol):
    async def get_by_id(self, offer_id: uuid.UUID) -> Offer | None: ...

    async def exists_by_source(self, source: str, source_listing_id: str) -> bool: ...

    async def upsert(self, offer: Offer) -> Offer: ...

    async def list_by_category(
        self, category: str, *, limit: int = 20, cursor: str | None = None
    ) -> list[Offer]: ...


class OfferServiceProtocol(Protocol):
    async def get_offer(self, offer_id: uuid.UUID) -> Offer: ...

    async def search_offers(self, *, category: str, query: str | None = None) -> list[Offer]: ...


class SearchProviderProtocol(Protocol):
    """Finds candidate listings for a category/query — returns lightweight
    references (ids or URLs), not full offer data (Band 07 pipeline step 1)."""

    async def search_listing_refs(
        self, *, category: OfferCategory, query: str | None, limit: int
    ) -> list[str]: ...


class OfferFetcherProtocol(Protocol):
    """Fetches full listing detail for one reference returned by a SearchProvider
    (Band 07 pipeline step 2). Some providers (e.g. an API that returns full
    summaries from search already) may not need a distinct fetch step."""

    async def fetch_raw(self, listing_ref: str, *, category: OfferCategory) -> RawListing: ...


class OfferNormalizerProtocol(Protocol):
    """Pure, deterministic mapping from provider-native data to the domain
    `Offer` model (Band 07 pipeline step 3). No I/O."""

    def normalize(self, raw: RawListing) -> Offer: ...


class OfferValidatorProtocol(Protocol):
    """Business-rule validation before persistence (Band 07 pipeline step 4).
    Returns a list of human-readable violation messages; empty = valid."""

    def validate(self, offer: Offer) -> list[str]: ...


class MarketplaceProviderProtocol(Protocol):
    """A complete, source-specific pipeline front end: composes search + fetch
    into ready-to-normalize `RawListing`s (Band 02: MarketplaceProvider)."""

    source: str

    async def search(
        self, *, category: OfferCategory, query: str | None = None, limit: int = 20
    ) -> list[RawListing]: ...


class SearchSchedulerProtocol(Protocol):
    """Runs the ingestion pipeline periodically for a set of configured
    (provider, category, query) jobs (Band 02: SearchScheduler,
    Band 07 deliverable: Scheduler foundation)."""

    async def run_once(self) -> None: ...

    def start(self) -> None: ...

    async def stop(self) -> None: ...
