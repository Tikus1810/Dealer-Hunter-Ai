"""The Band 07 ingestion pipeline: Source -> Provider -> Fetch -> Normalize
-> Validate -> Deduplicate -> Persist -> Trigger Analysis.

`MarketplaceProviderProtocol.search()` already covers Source/Provider/Fetch.
Deduplication is delegate to `OfferRepositoryProtocol.upsert()`, which is
idempotent on (source, source_listing_id) — see
`SqlAlchemyOfferRepository.upsert`. "Trigger Analysis" (handing the
persisted offer to DealBrain/RepairBrain) is left as an explicit extension
point below until those modules exist (Tasks #6/#7).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.modules.offers.application.interfaces import (
    MarketplaceProviderProtocol,
    OfferNormalizerProtocol,
    OfferPersistedHookProtocol,
    OfferRepositoryProtocol,
    OfferValidatorProtocol,
)
from app.modules.offers.domain.entities import Offer, OfferCategory

logger = get_logger(__name__)


@dataclass(slots=True)
class IngestionResult:
    fetched: int = 0
    normalized: int = 0
    rejected: int = 0
    persisted: int = 0
    errors: list[str] = field(default_factory=list)


class IngestionService:
    """Orchestrates one provider's pipeline run for a single category/query."""

    def __init__(
        self,
        provider: MarketplaceProviderProtocol,
        normalizer: OfferNormalizerProtocol,
        validator: OfferValidatorProtocol,
        offers: OfferRepositoryProtocol,
        *,
        on_offer_persisted: OfferPersistedHookProtocol | None = None,
    ) -> None:
        self._provider = provider
        self._normalizer = normalizer
        self._validator = validator
        self._offers = offers
        self._on_offer_persisted = on_offer_persisted

    async def ingest(
        self, *, category: OfferCategory, query: str | None = None, limit: int = 20
    ) -> IngestionResult:
        result = IngestionResult()
        raw_listings = await self._provider.search(category=category, query=query, limit=limit)

        for raw in raw_listings:
            result.fetched += 1
            try:
                offer = self._normalizer.normalize(raw)
            except Exception as exc:  # noqa: BLE001 — one bad listing must not abort the batch
                result.errors.append(f"normalize failed for {raw.source_listing_id!r}: {exc}")
                continue
            result.normalized += 1

            violations = self._validator.validate(offer)
            if violations:
                result.rejected += 1
                result.errors.extend(f"{offer.source_listing_id}: {v}" for v in violations)
                continue

            await self._persist(offer)
            result.persisted += 1

        logger.info(
            "ingestion_run_complete",
            provider=self._provider.source,
            category=category.value,
            fetched=result.fetched,
            normalized=result.normalized,
            rejected=result.rejected,
            persisted=result.persisted,
            error_count=len(result.errors),
        )
        return result

    async def _persist(self, offer: Offer) -> None:
        persisted = await self._offers.upsert(offer)
        if self._on_offer_persisted is not None:
            try:
                await self._on_offer_persisted(persisted)
            except Exception as exc:  # noqa: BLE001 — a hook failure must not lose the offer
                logger.error(
                    "offer_persisted_hook_failed",
                    offer_id=str(persisted.id),
                    error=str(exc),
                )
