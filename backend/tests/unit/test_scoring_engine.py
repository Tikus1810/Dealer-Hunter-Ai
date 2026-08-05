"""Unit tests for ScoringEngine and ExplanationGenerator — pure combination
logic, no I/O."""

from __future__ import annotations

import uuid

import pytest

from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.scoring.domain.entities import AnalyzerOutput, ExplanationFactor
from app.modules.scoring.domain.explanation import ExplanationGenerator
from app.modules.scoring.domain.scoring_engine import BASE_SCORE, SCORING_VERSION, ScoringEngine


def _offer() -> Offer:
    return Offer(
        id=uuid.uuid4(),
        source=OfferSource.EBAY,
        source_listing_id="1",
        title="MacBook Pro",
        description="desc",
        price_amount=900.0,
        price_currency="EUR",
        category=OfferCategory.MACBOOK,
        url="https://ebay.de/itm/1",
    )


class TestScoringEngine:
    def test_no_outputs_yields_base_score(self) -> None:
        engine = ScoringEngine()
        result = engine.combine(
            _offer(), [], estimated_market_value=900.0, estimated_total_cost=900.0
        )
        assert result.score == int(BASE_SCORE)
        assert result.confidence == 0.0
        assert result.scoring_version == SCORING_VERSION

    def test_positive_contributions_raise_score_above_base(self) -> None:
        engine = ScoringEngine()
        outputs = [
            AnalyzerOutput(20.0, 1.0, [ExplanationFactor("a", 20.0, "x")]),
            AnalyzerOutput(10.0, 1.0, [ExplanationFactor("b", 10.0, "y")]),
        ]
        result = engine.combine(
            _offer(), outputs, estimated_market_value=900.0, estimated_total_cost=900.0
        )
        assert result.score == int(BASE_SCORE) + 30
        assert result.confidence == 1.0
        assert len(result.explanation) == 2

    def test_score_is_clamped_to_0_100(self) -> None:
        engine = ScoringEngine()
        very_negative = [AnalyzerOutput(-1000.0, 1.0, [])]
        very_positive = [AnalyzerOutput(1000.0, 1.0, [])]
        low = engine.combine(
            _offer(), very_negative, estimated_market_value=900.0, estimated_total_cost=900.0
        )
        high = engine.combine(
            _offer(), very_positive, estimated_market_value=900.0, estimated_total_cost=900.0
        )
        assert low.score == 0
        assert high.score == 100

    def test_deterministic_for_identical_inputs(self) -> None:
        engine = ScoringEngine()
        offer = _offer()
        outputs = [AnalyzerOutput(5.0, 0.8, [ExplanationFactor("a", 5.0, "x")])]
        first = engine.combine(
            offer, outputs, estimated_market_value=900.0, estimated_total_cost=900.0
        )
        second = engine.combine(
            offer, outputs, estimated_market_value=900.0, estimated_total_cost=900.0
        )
        assert first == second


class TestExplanationGenerator:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (95, "Strong Buy"),
            (80, "Strong Buy"),
            (70, "Good Deal"),
            (65, "Good Deal"),
            (55, "Fair Deal"),
            (40, "Below Average"),
            (10, "Avoid"),
            (0, "Avoid"),
        ],
    )
    def test_recommendation_bands(self, score: int, expected: str) -> None:
        assert ExplanationGenerator().recommendation_for(score) == expected

    def test_finalize_sorts_factors_by_absolute_impact_descending(self) -> None:
        engine = ScoringEngine()
        outputs = [
            AnalyzerOutput(2.0, 1.0, [ExplanationFactor("small", 2.0, "x")]),
            AnalyzerOutput(-30.0, 1.0, [ExplanationFactor("big_negative", -30.0, "y")]),
            AnalyzerOutput(10.0, 1.0, [ExplanationFactor("medium", 10.0, "z")]),
        ]
        raw = engine.combine(
            _offer(), outputs, estimated_market_value=900.0, estimated_total_cost=900.0
        )

        finalized = ExplanationGenerator().finalize(raw)

        assert [f.name for f in finalized.explanation] == ["big_negative", "medium", "small"]
        assert finalized.recommendation  # non-empty
