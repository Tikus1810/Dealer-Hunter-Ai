"""Offer validation (Band 07 pipeline step 4). Pure, no I/O."""

from __future__ import annotations

from app.modules.offers.domain.entities import Offer

_MIN_TITLE_LENGTH = 5
_MAX_TITLE_LENGTH = 300
_MAX_PRICE_AMOUNT = 100_000.0
_ALLOWED_CURRENCIES = {"EUR", "USD", "GBP"}


class OfferValidator:
    """Implements `OfferValidatorProtocol`."""

    def validate(self, offer: Offer) -> list[str]:
        errors: list[str] = []

        title = offer.title.strip()
        if len(title) < _MIN_TITLE_LENGTH:
            errors.append(f"title too short: {len(title)} chars (min {_MIN_TITLE_LENGTH})")
        if len(title) > _MAX_TITLE_LENGTH:
            errors.append(f"title too long: {len(title)} chars (max {_MAX_TITLE_LENGTH})")

        if offer.price_amount <= 0:
            errors.append(f"price must be positive, got {offer.price_amount}")
        if offer.price_amount > _MAX_PRICE_AMOUNT:
            errors.append(f"price {offer.price_amount} exceeds sanity ceiling {_MAX_PRICE_AMOUNT}")

        if offer.price_currency not in _ALLOWED_CURRENCIES:
            errors.append(f"unsupported currency: {offer.price_currency!r}")

        if not offer.url:
            errors.append("missing listing url")

        if not offer.source_listing_id:
            errors.append("missing source_listing_id")

        return errors
