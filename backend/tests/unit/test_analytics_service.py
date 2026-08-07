"""Unit tests for AnalyticsService against an in-memory fake repository —
no DB, no HTTP."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.core.exceptions import ValidationError
from app.modules.analytics.application.service import AnalyticsService
from app.modules.analytics.domain.entities import AnalyticsEvent


class FakeAnalyticsEventRepository:
    def __init__(self) -> None:
        self.events: list[AnalyticsEvent] = []

    async def create(self, event: AnalyticsEvent) -> AnalyticsEvent:
        self.events.append(event)
        return event

    async def list_recent(self, name: str, *, limit: int = 100) -> list[AnalyticsEvent]:
        matching = [e for e in self.events if e.name == name]
        return matching[:limit]

    async def count_by_name(self, name: str, *, since: datetime | None = None) -> int:
        return len([e for e in self.events if e.name == name])

    async def count_distinct_users(self, name: str, *, since: datetime | None = None) -> int:
        return len({e.user_id for e in self.events if e.name == name and e.user_id is not None})

    async def purge_older_than(self, cutoff: datetime) -> int:
        before = len(self.events)
        self.events = [e for e in self.events if e.occurred_at is None or e.occurred_at >= cutoff]
        return before - len(self.events)


@pytest.fixture
def service() -> tuple[AnalyticsService, FakeAnalyticsEventRepository]:
    repo = FakeAnalyticsEventRepository()
    return AnalyticsService(repo), repo


async def test_track_persists_a_valid_event(
    service: tuple[AnalyticsService, FakeAnalyticsEventRepository],
) -> None:
    svc, repo = service
    user_id = uuid.uuid4()

    await svc.track("offer_viewed", user_id=user_id, properties={"category": "macbook"})

    assert len(repo.events) == 1
    assert repo.events[0].name == "offer_viewed"
    assert repo.events[0].user_id == user_id
    assert repo.events[0].properties == {"category": "macbook"}


async def test_track_allows_anonymous_events(
    service: tuple[AnalyticsService, FakeAnalyticsEventRepository],
) -> None:
    svc, repo = service
    await svc.track("app_opened", user_id=None, properties={})
    assert repo.events[0].user_id is None


@pytest.mark.parametrize(
    "bad_name",
    [
        "",  # empty
        "Offer-Viewed",  # not snake_case
        "OFFER_VIEWED",  # uppercase
        "1_offer_viewed",  # can't start with a digit
        "a" * 121,  # too long
    ],
)
async def test_track_rejects_malformed_event_names(
    service: tuple[AnalyticsService, FakeAnalyticsEventRepository], bad_name: str
) -> None:
    svc, _repo = service
    with pytest.raises(ValidationError):
        await svc.track(bad_name, user_id=None, properties={})


async def test_track_rejects_denylisted_property_keys(
    service: tuple[AnalyticsService, FakeAnalyticsEventRepository],
) -> None:
    svc, _repo = service
    with pytest.raises(ValidationError):
        await svc.track("user_registered", user_id=None, properties={"email": "a@example.com"})


async def test_track_rejects_too_many_properties(
    service: tuple[AnalyticsService, FakeAnalyticsEventRepository],
) -> None:
    svc, _repo = service
    too_many = {f"key_{i}": i for i in range(26)}
    with pytest.raises(ValidationError):
        await svc.track("offer_viewed", user_id=None, properties=too_many)


async def test_track_rejects_oversized_string_property_values(
    service: tuple[AnalyticsService, FakeAnalyticsEventRepository],
) -> None:
    svc, _repo = service
    with pytest.raises(ValidationError):
        await svc.track("offer_viewed", user_id=None, properties={"note": "x" * 501})


async def test_summary_counts_events_and_distinct_users(
    service: tuple[AnalyticsService, FakeAnalyticsEventRepository],
) -> None:
    svc, _repo = service
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    await svc.track("offer_favorited", user_id=user_a, properties={})
    await svc.track("offer_favorited", user_id=user_a, properties={})  # same user again
    await svc.track("offer_favorited", user_id=user_b, properties={})
    await svc.track("offer_favorited", user_id=None, properties={})  # anonymous

    summary = await svc.summary("offer_favorited")

    assert summary.count == 4
    assert summary.distinct_users == 2  # anonymous events don't count toward reach


async def test_purge_events_older_than_rejects_non_positive_days(
    service: tuple[AnalyticsService, FakeAnalyticsEventRepository],
) -> None:
    svc, _repo = service
    with pytest.raises(ValidationError):
        await svc.purge_events_older_than(0)
