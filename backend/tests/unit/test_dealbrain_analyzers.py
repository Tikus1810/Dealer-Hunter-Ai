"""Unit tests for the DealBrain analyzers — pure logic, no I/O."""

from __future__ import annotations

import uuid

import pytest

from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.repair.domain.entities import RepairDifficulty, RepairReport
from app.modules.scoring.domain.analyzers import (
    PriceAnalyzer,
    RepairFeasibilityAnalyzer,
    RiskAnalyzer,
    SellerAnalyzer,
    SpecificationAnalyzer,
)


def _offer(**overrides: object) -> Offer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": OfferSource.EBAY,
        "source_listing_id": "1",
        "title": "Apple MacBook Pro 14 M3",
        "description": "Guter Zustand, wenig benutzt.",
        "price_amount": 900.0,
        "price_currency": "EUR",
        "category": OfferCategory.MACBOOK,
        "images": ["a.jpg", "b.jpg", "c.jpg"],
        "location": "Berlin",
        "url": "https://ebay.de/itm/1",
    }
    defaults.update(overrides)
    return Offer(**defaults)  # type: ignore[arg-type]


class TestPriceAnalyzer:
    def test_price_below_comparables_median_boosts_score(self) -> None:
        analyzer = PriceAnalyzer()
        output, market_value = analyzer.analyze(
            _offer(price_amount=800.0), comparable_prices=[1000, 1000, 1000]
        )
        assert market_value == 1000.0
        assert output.score_contribution > 0
        assert output.confidence == 1.0

    def test_price_above_comparables_median_penalizes_score(self) -> None:
        analyzer = PriceAnalyzer()
        output, market_value = analyzer.analyze(
            _offer(price_amount=1200.0), comparable_prices=[1000, 1000, 1000]
        )
        assert output.score_contribution < 0

    def test_no_comparables_falls_back_to_own_price_with_low_confidence(self) -> None:
        analyzer = PriceAnalyzer()
        output, market_value = analyzer.analyze(_offer(price_amount=800.0), comparable_prices=[])
        assert market_value == 800.0
        assert output.score_contribution == 0.0  # own price vs itself => no discount
        assert output.confidence == 0.2

    def test_score_contribution_is_capped(self) -> None:
        analyzer = PriceAnalyzer()
        output, _ = analyzer.analyze(
            _offer(price_amount=1.0), comparable_prices=[10_000, 10_000, 10_000]
        )
        assert output.score_contribution == analyzer.MAX_SCORE_SWING

    def test_deterministic_for_identical_inputs(self) -> None:
        analyzer = PriceAnalyzer()
        offer = _offer(price_amount=800.0)
        first, _ = analyzer.analyze(offer, [900, 950, 1000])
        second, _ = analyzer.analyze(offer, [900, 950, 1000])
        assert first == second


class TestSpecificationAnalyzer:
    def test_positive_condition_keywords_boost_score(self) -> None:
        output = SpecificationAnalyzer().analyze(_offer(description="Wie neu, OVP vorhanden."))
        assert output.score_contribution > 0

    def test_negative_condition_keywords_penalize_score(self) -> None:
        output = SpecificationAnalyzer().analyze(
            _offer(description="Display defekt, Riss im Gehäuse.")
        )
        assert output.score_contribution < 0

    def test_no_images_penalizes_score_and_confidence(self) -> None:
        output = SpecificationAnalyzer().analyze(_offer(images=[]))
        assert output.score_contribution < 0
        assert output.confidence < 1.0

    def test_thin_description_penalizes(self) -> None:
        output = SpecificationAnalyzer().analyze(_offer(description="ok"))
        assert any(f.name == "thin_description" for f in output.factors)


class TestSellerAnalyzer:
    def test_missing_rating_is_neutral_but_lowers_confidence(self) -> None:
        output = SellerAnalyzer().analyze(_offer(seller_rating=None))
        assert output.score_contribution == 0.0
        assert output.confidence < 1.0

    def test_high_rating_boosts_score(self) -> None:
        output = SellerAnalyzer().analyze(_offer(seller_rating=100.0))
        assert output.score_contribution > 0
        assert output.confidence == 1.0

    def test_low_rating_penalizes_score(self) -> None:
        output = SellerAnalyzer().analyze(_offer(seller_rating=60.0))
        assert output.score_contribution < 0


class TestRiskAnalyzer:
    def test_no_risk_indicators_by_default(self) -> None:
        output = RiskAnalyzer().analyze(_offer())
        assert output.score_contribution == 0.0
        assert output.factors[0].name == "no_risk_indicators"

    def test_scam_keywords_penalize_heavily(self) -> None:
        output = RiskAnalyzer().analyze(
            _offer(description="Bitte nur Vorkasse, keine Besichtigung möglich.")
        )
        assert output.score_contribution <= -30.0

    def test_missing_location_penalizes(self) -> None:
        output = RiskAnalyzer().analyze(_offer(location=None))
        assert output.score_contribution < 0

    def test_implausible_price_penalizes(self) -> None:
        output = RiskAnalyzer().analyze(_offer(price_amount=0.5))
        assert output.score_contribution < 0


class TestRepairFeasibilityAnalyzer:
    @pytest.mark.parametrize(
        ("repair_score", "expect_positive"),
        [(90, True), (10, False)],
    )
    def test_repair_score_direction(self, repair_score: int, expect_positive: bool) -> None:
        report = RepairReport(
            offer_id=uuid.uuid4(),
            repair_score=repair_score,
            estimated_repair_cost=50.0,
            estimated_repair_time_hours=1.0,
            difficulty=RepairDifficulty.BEGINNER,
        )
        output = RepairFeasibilityAnalyzer().analyze(report)
        assert (output.score_contribution > 0) is expect_positive
