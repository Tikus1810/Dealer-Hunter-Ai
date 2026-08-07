"""Unit tests for app.core.ai_rules — the shared score/confidence
invariant checks (Band 16: AI Rules)."""

from __future__ import annotations

import uuid

import pytest

from app.core.ai_rules import validate_confidence, validate_score
from app.modules.repair.domain.entities import RepairDifficulty, RepairReport
from app.modules.scoring.domain.entities import AnalyzerOutput, DealScoreResult
from app.modules.vision.domain.entities import CosmeticAssessment, VisionObservation


@pytest.mark.parametrize("value", [0, 50, 100])
def test_validate_score_accepts_the_full_default_range(value: int) -> None:
    validate_score("x", value)  # must not raise


@pytest.mark.parametrize("value", [-1, 101])
def test_validate_score_rejects_outside_the_default_range(value: int) -> None:
    with pytest.raises(ValueError, match="x"):
        validate_score("x", value)


@pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
def test_validate_confidence_accepts_0_to_1(value: float) -> None:
    validate_confidence("x", value)  # must not raise


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_validate_confidence_rejects_outside_0_to_1(value: float) -> None:
    with pytest.raises(ValueError, match="x"):
        validate_confidence("x", value)


def test_deal_score_result_rejects_an_out_of_range_score() -> None:
    with pytest.raises(ValueError, match="score"):
        DealScoreResult(
            offer_id=uuid.uuid4(),
            score=101,
            confidence=0.5,
            estimated_market_value=100.0,
            estimated_total_cost=90.0,
            recommendation="buy",
        )


def test_deal_score_result_rejects_an_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        DealScoreResult(
            offer_id=uuid.uuid4(),
            score=50,
            confidence=1.5,
            estimated_market_value=100.0,
            estimated_total_cost=90.0,
            recommendation="buy",
        )


def test_analyzer_output_rejects_an_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        AnalyzerOutput(score_contribution=1000.0, confidence=2.0)


def test_analyzer_output_allows_an_unbounded_score_contribution() -> None:
    # score_contribution is a signed delta, not a final score — only
    # confidence has a fixed range (see AnalyzerOutput.__post_init__).
    AnalyzerOutput(score_contribution=-1000.0, confidence=1.0)  # must not raise


def test_repair_report_rejects_an_out_of_range_repair_score() -> None:
    with pytest.raises(ValueError, match="repair_score"):
        RepairReport(
            offer_id=uuid.uuid4(),
            repair_score=-1,
            estimated_repair_cost=50.0,
            estimated_repair_time_hours=1.0,
            difficulty=RepairDifficulty.BEGINNER,
        )


def test_cosmetic_assessment_rejects_an_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        CosmeticAssessment(
            condition="good",
            confidence=1.5,
            observed_damage=[],
            uncertain_notes=[],
            missing_components=[],
            reasoning="x",
            model_used="claude-opus-5",
            prompt_version="1.0.0",
        )


def test_vision_observation_rejects_an_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        VisionObservation(
            offer_id=uuid.uuid4(),
            image_count=1,
            is_image_set_incomplete=False,
            confidence=-0.1,
        )
