"""Unit tests for RepairBrainService against in-memory fakes — no DB, no HTTP."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import NotFoundError
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.repair.application.service import RepairBrainService
from app.modules.repair.domain.entities import RepairReport


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
        raise NotImplementedError


class FakeRepairReportRepository:
    def __init__(self) -> None:
        self.saved: list[RepairReport] = []

    async def save(self, report: RepairReport) -> None:
        self.saved.append(report)

    async def get_latest_for_offer(self, offer_id: uuid.UUID) -> RepairReport | None:
        matches = [r for r in self.saved if r.offer_id == offer_id]
        return matches[-1] if matches else None


def _offer(**overrides: object) -> Offer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": OfferSource.EBAY,
        "source_listing_id": "1",
        "title": "MacBook Pro 13",
        "description": "Akku schwach, sonst top.",
        "price_amount": 500.0,
        "price_currency": "EUR",
        "category": OfferCategory.MACBOOK,
        "url": "https://ebay.de/itm/1",
    }
    defaults.update(overrides)
    return Offer(**defaults)  # type: ignore[arg-type]


async def test_analyze_raises_not_found_for_unknown_offer() -> None:
    service = RepairBrainService(FakeOfferRepository([]), FakeRepairReportRepository())
    with pytest.raises(NotFoundError):
        await service.analyze(uuid.uuid4(), reported_defects=[])


async def test_analyze_persists_and_returns_report() -> None:
    offer = _offer()
    offers_repo = FakeOfferRepository([offer])
    reports_repo = FakeRepairReportRepository()
    service = RepairBrainService(offers_repo, reports_repo)

    report = await service.analyze(offer.id, reported_defects=["Akku defekt"])

    assert report.offer_id == offer.id
    assert 0 <= report.repair_score <= 100
    assert report.estimated_repair_cost > 0
    assert report.summary
    assert len(reports_repo.saved) == 1
    assert reports_repo.saved[0] == report


async def test_analyze_picks_up_inferred_fault_from_listing_text() -> None:
    offer = _offer(description="Display defekt, Riss im Gehäuse.")
    service = RepairBrainService(FakeOfferRepository([offer]), FakeRepairReportRepository())

    report = await service.analyze(offer.id, reported_defects=[])

    assert any("inferred" in note for note in report.risk_notes)


async def test_analyze_is_deterministic_for_identical_inputs() -> None:
    offer = _offer()
    offers_repo = FakeOfferRepository([offer])

    service_a = RepairBrainService(offers_repo, FakeRepairReportRepository())
    service_b = RepairBrainService(offers_repo, FakeRepairReportRepository())

    report_a = await service_a.analyze(offer.id, reported_defects=["Akku defekt"])
    report_b = await service_b.analyze(offer.id, reported_defects=["Akku defekt"])

    assert report_a.repair_score == report_b.repair_score
    assert report_a.estimated_repair_cost == report_b.estimated_repair_cost
    assert report_a.difficulty == report_b.difficulty
