"""Unit tests for DealBrainService against in-memory fakes — no DB, no HTTP."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import NotFoundError
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.repair.domain.entities import RepairDifficulty, RepairReport
from app.modules.scoring.application.service import DealBrainService
from app.modules.scoring.domain.entities import DealScoreResult


class FakeOfferRepository:
    def __init__(self, offers: list[Offer]) -> None:
        self._offers = {o.id: o for o in offers}

    async def get_by_id(self, offer_id: uuid.UUID) -> Offer | None:
        return self._offers.get(offer_id)

    async def exists_by_source(self, source: str, source_listing_id: str) -> bool:
        raise NotImplementedError

    async def upsert(self, offer: Offer) -> Offer:
        raise NotImplementedError

    async def list_by_category(
        self, category: str, *, limit: int = 20, cursor: str | None = None
    ) -> list[Offer]:
        return [o for o in self._offers.values() if o.category.value == category][:limit]


class FakeDealScoreRepository:
    def __init__(self) -> None:
        self.saved: list[DealScoreResult] = []

    async def save(self, result: DealScoreResult) -> None:
        self.saved.append(result)

    async def get_latest_for_offer(self, offer_id: uuid.UUID) -> DealScoreResult | None:
        matches = [r for r in self.saved if r.offer_id == offer_id]
        return matches[-1] if matches else None


def _offer(price: float = 900.0, **overrides: object) -> Offer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": OfferSource.EBAY,
        "source_listing_id": str(uuid.uuid4()),
        "title": "Apple MacBook Pro 14 M3, wie neu",
        "description": "OVP vorhanden, kaum genutzt.",
        "price_amount": price,
        "price_currency": "EUR",
        "category": OfferCategory.MACBOOK,
        "images": ["a.jpg", "b.jpg", "c.jpg"],
        "location": "Berlin",
        "seller_rating": 99.0,
        "url": "https://ebay.de/itm/x",
    }
    defaults.update(overrides)
    return Offer(**defaults)  # type: ignore[arg-type]


async def test_score_offer_raises_not_found_for_unknown_offer() -> None:
    service = DealBrainService(FakeOfferRepository([]), FakeDealScoreRepository())
    with pytest.raises(NotFoundError):
        await service.score_offer(uuid.uuid4())


async def test_score_offer_persists_and_returns_result_with_recommendation() -> None:
    target = _offer(price=800.0)
    comparables = [_offer(price=1000.0), _offer(price=1000.0), _offer(price=1000.0)]
    offers_repo = FakeOfferRepository([target, *comparables])
    scores_repo = FakeDealScoreRepository()
    service = DealBrainService(offers_repo, scores_repo)

    result = await service.score_offer(target.id)

    assert result.offer_id == target.id
    assert 0 <= result.score <= 100
    assert result.recommendation  # non-empty, set by ExplanationGenerator
    assert result.estimated_market_value == 1000.0
    assert result.estimated_total_cost == 800.0  # no repair report supplied
    assert len(scores_repo.saved) == 1
    assert scores_repo.saved[0] == result


async def test_score_offer_excludes_itself_from_comparables() -> None:
    target = _offer(price=800.0)
    offers_repo = FakeOfferRepository([target])  # only itself in the category
    service = DealBrainService(offers_repo, FakeDealScoreRepository())

    result = await service.score_offer(target.id)

    # No comparables besides itself => falls back to own price as baseline.
    assert result.estimated_market_value == 800.0


async def test_score_offer_with_repair_report_adds_cost_and_factor() -> None:
    target = _offer(price=500.0)
    offers_repo = FakeOfferRepository([target])
    service = DealBrainService(offers_repo, FakeDealScoreRepository())
    repair_report = RepairReport(
        offer_id=target.id,
        repair_score=80,
        estimated_repair_cost=100.0,
        estimated_repair_time_hours=2.0,
        difficulty=RepairDifficulty.INTERMEDIATE,
    )

    result = await service.score_offer(target.id, repair_report=repair_report)

    assert result.estimated_total_cost == 600.0
    assert any(f.name == "repair_feasibility" for f in result.explanation)


async def test_score_offer_without_repair_report_flags_it_as_unavailable() -> None:
    target = _offer(price=500.0)
    offers_repo = FakeOfferRepository([target])
    service = DealBrainService(offers_repo, FakeDealScoreRepository())

    result = await service.score_offer(target.id)

    assert any(f.name == "repair_assessment_unavailable" for f in result.explanation)


async def test_score_offer_is_deterministic_for_identical_inputs() -> None:
    target = _offer(price=800.0)
    comparables = [_offer(price=1000.0), _offer(price=1000.0), _offer(price=1000.0)]
    offers_repo = FakeOfferRepository([target, *comparables])

    service_a = DealBrainService(offers_repo, FakeDealScoreRepository())
    service_b = DealBrainService(offers_repo, FakeDealScoreRepository())

    result_a = await service_a.score_offer(target.id)
    result_b = await service_b.score_offer(target.id)

    assert result_a.score == result_b.score
    assert result_a.confidence == result_b.confidence
    assert result_a.recommendation == result_b.recommendation
