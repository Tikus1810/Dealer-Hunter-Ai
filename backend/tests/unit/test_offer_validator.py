"""Unit tests for OfferValidator — pure business rules, no I/O."""

from __future__ import annotations

import uuid

import pytest

from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.offers.infrastructure.validator import OfferValidator


@pytest.fixture
def validator() -> OfferValidator:
    return OfferValidator()


def _valid_offer(**overrides: object) -> Offer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": OfferSource.EBAY,
        "source_listing_id": "1",
        "title": "Apple MacBook Pro 14 M3",
        "description": "Good condition",
        "price_amount": 899.0,
        "price_currency": "EUR",
        "category": OfferCategory.MACBOOK,
        "url": "https://ebay.de/itm/1",
    }
    defaults.update(overrides)
    return Offer(**defaults)  # type: ignore[arg-type]


def test_valid_offer_has_no_errors(validator: OfferValidator) -> None:
    assert validator.validate(_valid_offer()) == []


def test_rejects_too_short_title(validator: OfferValidator) -> None:
    errors = validator.validate(_valid_offer(title="Hi"))
    assert any("title too short" in e for e in errors)


def test_rejects_zero_or_negative_price(validator: OfferValidator) -> None:
    assert any("positive" in e for e in validator.validate(_valid_offer(price_amount=0)))
    assert any("positive" in e for e in validator.validate(_valid_offer(price_amount=-10)))


def test_rejects_unreasonably_high_price(validator: OfferValidator) -> None:
    errors = validator.validate(_valid_offer(price_amount=999_999))
    assert any("sanity ceiling" in e for e in errors)


def test_rejects_unsupported_currency(validator: OfferValidator) -> None:
    errors = validator.validate(_valid_offer(price_currency="JPY"))
    assert any("unsupported currency" in e for e in errors)


def test_rejects_missing_url(validator: OfferValidator) -> None:
    errors = validator.validate(_valid_offer(url=""))
    assert any("missing listing url" in e for e in errors)


def test_accumulates_multiple_errors(validator: OfferValidator) -> None:
    errors = validator.validate(_valid_offer(title="x", price_amount=-1, url=""))
    assert len(errors) == 3
