"""Offer normalization (Band 07 pipeline step 3): provider-native `RawListing`
-> domain `Offer`. Pure and deterministic — no I/O, no persistence.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.offers.domain.entities import Offer, OfferSource, RawListing


class OfferNormalizer:
    """Implements `OfferNormalizerProtocol`. Dispatches by `raw.source` so a
    single instance can normalize listings from every provider."""

    def normalize(self, raw: RawListing) -> Offer:
        if raw.source is OfferSource.EBAY:
            return self._normalize_ebay(raw)
        if raw.source is OfferSource.EBAY_KLEINANZEIGEN:
            return self._normalize_kleinanzeigen(raw)
        raise ValueError(f"no normalizer registered for source {raw.source!r}")

    def _normalize_ebay(self, raw: RawListing) -> Offer:
        """Maps an eBay Browse API `item_summary` object.
        https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
        """
        p = raw.payload
        price = p.get("price", {})
        image = p.get("image", {}).get("imageUrl")
        thumbnails = [
            img["imageUrl"] for img in p.get("thumbnailImages", []) if img.get("imageUrl")
        ]
        images = [image, *thumbnails] if image else thumbnails

        return Offer(
            id=uuid.uuid4(),
            source=raw.source,
            source_listing_id=raw.source_listing_id,
            title=p.get("title", ""),
            description=p.get("shortDescription", "") or p.get("title", ""),
            price_amount=float(price.get("value", 0)),
            price_currency=price.get("currency", "EUR"),
            category=raw.category,
            images=images,
            location=(p.get("itemLocation", {}).get("city")),
            seller_name=p.get("seller", {}).get("username"),
            seller_rating=self._parse_ebay_feedback_percentage(p),
            url=p.get("itemWebUrl", ""),
            created_at=datetime.now(UTC),
            fetched_at=datetime.now(UTC),
        )

    @staticmethod
    def _parse_ebay_feedback_percentage(payload: dict[str, Any]) -> float | None:
        raw_pct = payload.get("seller", {}).get("feedbackPercentage")
        if raw_pct is None:
            return None
        try:
            return float(raw_pct)
        except (TypeError, ValueError):
            return None

    def _normalize_kleinanzeigen(self, raw: RawListing) -> Offer:
        """Maps the fields extracted by `KleinanzeigenProvider`'s HTML parser."""
        p = raw.payload
        return Offer(
            id=uuid.uuid4(),
            source=raw.source,
            source_listing_id=raw.source_listing_id,
            title=p.get("title", ""),
            description=p.get("description", ""),
            price_amount=float(p.get("price_amount") or 0),
            price_currency="EUR",
            category=raw.category,
            images=p.get("images", []),
            location=p.get("location"),
            seller_name=p.get("seller_name"),
            seller_rating=None,  # not exposed on Kleinanzeigen listing/search pages
            url=p.get("url", ""),
            created_at=datetime.now(UTC),
            fetched_at=datetime.now(UTC),
        )
