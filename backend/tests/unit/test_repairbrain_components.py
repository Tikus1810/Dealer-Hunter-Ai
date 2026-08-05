"""Unit tests for RepairBrain's domain components — pure logic, no I/O."""

from __future__ import annotations

import uuid

from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.repair.domain.cost_estimator import CostEstimator
from app.modules.repair.domain.entities import DetectedFault, RepairDifficulty, ReplacementPart
from app.modules.repair.domain.fault_analyzer import FaultAnalyzer
from app.modules.repair.domain.parts_resolver import PartsResolver
from app.modules.repair.domain.recommendation import RecommendationGenerator
from app.modules.repair.domain.scoring_engine import RepairScoringEngine
from app.modules.repair.domain.time_estimator import TimeEstimator


def _offer(**overrides: object) -> Offer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": OfferSource.EBAY,
        "source_listing_id": "1",
        "title": "MacBook Pro 13",
        "description": "Funktioniert einwandfrei.",
        "price_amount": 500.0,
        "price_currency": "EUR",
        "category": OfferCategory.MACBOOK,
        "url": "https://ebay.de/itm/1",
    }
    defaults.update(overrides)
    return Offer(**defaults)  # type: ignore[arg-type]


class TestFaultAnalyzer:
    def test_reported_defect_is_confirmed(self) -> None:
        faults = FaultAnalyzer().analyze(_offer(), ["Akku defekt"])
        assert len(faults) == 1
        assert faults[0].category == "battery"
        assert faults[0].is_confirmed is True

    def test_unrecognized_reported_defect_maps_to_other_but_stays_confirmed(self) -> None:
        faults = FaultAnalyzer().analyze(_offer(), ["Kratzer auf dem Gehäuse"])
        assert len(faults) == 1
        assert faults[0].category == "other"
        assert faults[0].is_confirmed is True

    def test_listing_text_produces_inferred_fault(self) -> None:
        faults = FaultAnalyzer().analyze(
            _offer(description="Displayschaden vorhanden, sonst funktionsfähig."), []
        )
        assert len(faults) == 1
        assert faults[0].category == "display"
        assert faults[0].is_confirmed is False

    def test_confirmed_defect_suppresses_duplicate_inferred_match(self) -> None:
        faults = FaultAnalyzer().analyze(
            _offer(description="Displayschaden vorhanden."), ["Display defekt"]
        )
        assert len(faults) == 1
        assert faults[0].is_confirmed is True

    def test_no_defects_and_clean_text_yields_no_faults(self) -> None:
        assert FaultAnalyzer().analyze(_offer(), []) == []


class TestPartsResolver:
    def test_resolve_parts_maps_known_fault_for_category(self) -> None:
        faults = [DetectedFault("battery", True, "Akku defekt")]
        parts = PartsResolver().resolve_parts(faults, OfferCategory.MACBOOK)
        assert len(parts) == 1
        assert "battery" in parts[0].name.lower()
        assert parts[0].estimated_price > 0

    def test_resolve_parts_deduplicates_same_part(self) -> None:
        faults = [
            DetectedFault("battery", True, "a"),
            DetectedFault("battery", False, "b"),
        ]
        parts = PartsResolver().resolve_parts(faults, OfferCategory.MACBOOK)
        assert len(parts) == 1

    def test_resolve_parts_unknown_fault_category_yields_placeholder(self) -> None:
        faults = [DetectedFault("other", True, "Kratzer")]
        parts = PartsResolver().resolve_parts(faults, OfferCategory.MACBOOK)
        assert len(parts) == 1
        assert parts[0].availability == "unknown"

    def test_resolve_tools_no_faults_returns_default(self) -> None:
        tools = PartsResolver().resolve_tools([])
        assert tools  # non-empty default toolkit

    def test_resolve_tools_deduplicates(self) -> None:
        faults = [DetectedFault("display", True, "a"), DetectedFault("battery", True, "b")]
        tools = PartsResolver().resolve_tools(faults)
        assert len(tools) == len(set(tools))


class TestTimeEstimator:
    def test_no_faults_zero_time_beginner_difficulty(self) -> None:
        estimate = TimeEstimator().estimate([])
        assert estimate.hours == 0.0
        assert estimate.difficulty == RepairDifficulty.BEGINNER

    def test_difficulty_is_the_hardest_of_all_faults(self) -> None:
        faults = [
            DetectedFault("battery", True, "a"),  # beginner
            DetectedFault("water_damage", True, "b"),  # advanced
        ]
        estimate = TimeEstimator().estimate(faults)
        assert estimate.difficulty == RepairDifficulty.ADVANCED

    def test_hours_sum_across_faults(self) -> None:
        faults = [DetectedFault("battery", True, "a"), DetectedFault("keyboard", True, "b")]
        estimate = TimeEstimator().estimate(faults)
        assert estimate.hours == 0.5 + 0.75


class TestCostEstimator:
    def test_zero_parts_zero_time_is_zero_cost(self) -> None:
        assert CostEstimator().estimate([], 0.0) == 0.0

    def test_cost_combines_parts_and_labor(self) -> None:
        parts = [ReplacementPart("Battery", 70.0, "in_stock")]
        cost = CostEstimator().estimate(parts, 1.0)
        assert cost == 70.0 + CostEstimator().estimate([], 1.0)


class TestRepairScoringEngine:
    def test_no_faults_yields_high_score(self) -> None:
        score = RepairScoringEngine().score([], RepairDifficulty.BEGINNER, 0.0)
        assert score >= 80

    def test_more_faults_lower_score(self) -> None:
        few = RepairScoringEngine().score(
            [DetectedFault("battery", True, "a")], RepairDifficulty.BEGINNER, 50.0
        )
        many = RepairScoringEngine().score(
            [
                DetectedFault("battery", True, "a"),
                DetectedFault("display", True, "b"),
                DetectedFault("hinge", True, "c"),
            ],
            RepairDifficulty.INTERMEDIATE,
            300.0,
        )
        assert many < few

    def test_inferred_faults_score_lower_than_confirmed(self) -> None:
        confirmed = RepairScoringEngine().score(
            [DetectedFault("battery", True, "a")], RepairDifficulty.BEGINNER, 50.0
        )
        inferred = RepairScoringEngine().score(
            [DetectedFault("battery", False, "a")], RepairDifficulty.BEGINNER, 50.0
        )
        assert inferred < confirmed

    def test_score_is_clamped_to_0_100(self) -> None:
        many_faults = [DetectedFault("water_damage", True, str(i)) for i in range(20)]
        score = RepairScoringEngine().score(many_faults, RepairDifficulty.ADVANCED, 10_000.0)
        assert score == 0

    def test_deterministic_for_identical_inputs(self) -> None:
        faults = [DetectedFault("battery", True, "a")]
        engine = RepairScoringEngine()
        assert engine.score(faults, RepairDifficulty.BEGINNER, 50.0) == engine.score(
            faults, RepairDifficulty.BEGINNER, 50.0
        )


class TestRecommendationGenerator:
    def test_inferred_fault_gets_a_risk_note(self) -> None:
        faults = [DetectedFault("display", False, "displayschaden")]
        _summary, risk_notes = RecommendationGenerator().summarize(
            faults, RepairDifficulty.INTERMEDIATE, 60, 100.0, 1.0
        )
        assert any("inferred" in note for note in risk_notes)

    def test_no_faults_still_produces_a_risk_note(self) -> None:
        _summary, risk_notes = RecommendationGenerator().summarize(
            [], RepairDifficulty.BEGINNER, 90, 0.0, 0.0
        )
        assert len(risk_notes) == 1

    def test_high_score_verdict_is_positive(self) -> None:
        summary, _ = RecommendationGenerator().summarize(
            [], RepairDifficulty.BEGINNER, 90, 0.0, 0.0
        )
        assert "worthwhile" in summary.lower()

    def test_low_score_verdict_is_negative(self) -> None:
        faults = [DetectedFault("water_damage", True, "a")]
        summary, _ = RecommendationGenerator().summarize(
            faults, RepairDifficulty.ADVANCED, 10, 500.0, 3.0
        )
        assert "not worthwhile" in summary.lower()
