"""Unit tests for OfferNormalizer — pure mapping logic, no I/O."""

from __future__ import annotations

import pytest

from app.modules.offers.domain.entities import OfferCategory, OfferSource, RawListing
from app.modules.offers.infrastructure.normalizer import OfferNormalizer


@pytest.fixture
def normalizer() -> OfferNormalizer:
    return OfferNormalizer()


def test_normalize_ebay_maps_core_fields(normalizer: OfferNormalizer) -> None:
    raw = RawListing(
        source=OfferSource.EBAY,
        source_listing_id="v1|123456789|0",
        category=OfferCategory.MACBOOK,
        payload={
            "title": "Apple MacBook Pro 14 M3, sehr guter Zustand",
            "shortDescription": "Kaum genutzt, OVP vorhanden.",
            "price": {"value": "899.00", "currency": "EUR"},
            "itemLocation": {"city": "Berlin"},
            "seller": {"username": "tech_deals_de", "feedbackPercentage": "99.5"},
            "itemWebUrl": "https://www.ebay.de/itm/123456789",
            "image": {"imageUrl": "https://i.ebayimg.com/main.jpg"},
            "thumbnailImages": [{"imageUrl": "https://i.ebayimg.com/thumb1.jpg"}],
        },
    )

    offer = normalizer.normalize(raw)

    assert offer.source is OfferSource.EBAY
    assert offer.source_listing_id == "v1|123456789|0"
    assert offer.title == "Apple MacBook Pro 14 M3, sehr guter Zustand"
    assert offer.price_amount == 899.0
    assert offer.price_currency == "EUR"
    assert offer.category is OfferCategory.MACBOOK
    assert offer.location == "Berlin"
    assert offer.seller_name == "tech_deals_de"
    assert offer.seller_rating == 99.5
    assert offer.url == "https://www.ebay.de/itm/123456789"
    assert offer.images == ["https://i.ebayimg.com/main.jpg", "https://i.ebayimg.com/thumb1.jpg"]


def test_normalize_ebay_handles_missing_optional_fields(normalizer: OfferNormalizer) -> None:
    raw = RawListing(
        source=OfferSource.EBAY,
        source_listing_id="v1|1|0",
        category=OfferCategory.IPHONE,
        payload={"title": "iPhone 13", "price": {"value": "450"}},
    )

    offer = normalizer.normalize(raw)

    assert offer.title == "iPhone 13"
    assert offer.price_amount == 450.0
    assert offer.price_currency == "EUR"  # normalizer default when absent
    assert offer.seller_rating is None
    assert offer.images == []


def test_normalize_kleinanzeigen_maps_core_fields(normalizer: OfferNormalizer) -> None:
    raw = RawListing(
        source=OfferSource.EBAY_KLEINANZEIGEN,
        source_listing_id="3165525229",
        category=OfferCategory.MACBOOK,
        payload={
            "title": "MacBook Air M1 2020",
            "description": "Kaum Gebrauchsspuren, Akku 92%.",
            "price_amount": 650.0,
            "location": "10827 Berlin - Schöneberg",
            "images": ["https://img.kleinanzeigen.de/example.jpg"],
            "url": "https://www.kleinanzeigen.de/s-anzeige/macbook-air-m1/3165525229",
            "seller_name": None,
        },
    )

    offer = normalizer.normalize(raw)

    assert offer.source is OfferSource.EBAY_KLEINANZEIGEN
    assert offer.price_amount == 650.0
    assert offer.price_currency == "EUR"
    assert offer.location == "10827 Berlin - Schöneberg"
    assert offer.seller_rating is None  # never exposed by this source


def test_normalize_unknown_source_raises(normalizer: OfferNormalizer) -> None:
    raw = RawListing(
        source="unknown_source",  # type: ignore[arg-type]
        source_listing_id="1",
        category=OfferCategory.IPHONE,
        payload={},
    )
    with pytest.raises(ValueError, match="no normalizer registered"):
        normalizer.normalize(raw)
