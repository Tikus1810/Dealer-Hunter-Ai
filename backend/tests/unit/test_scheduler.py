"""Unit tests for AsyncIntervalScheduler (Band 07/13: the marketplace
ingestion scheduler, built in Task #5, finally given a real call site from
app/bootstrap.py in Task #14). `SqlAlchemyOfferRepository` is monkeypatched
out (it issues real SQLAlchemy `select()` statements a hand-rolled fake
session can't usefully serve — see tests/integration/test_offer_repository.py
for that coverage) so this file stays fakes-only: no real DB, no asyncio
sleeping longer than the test needs.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable

import pytest

from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource, RawListing
from app.modules.offers.infrastructure import scheduler as scheduler_module
from app.modules.offers.infrastructure.scheduler import AsyncIntervalScheduler, ScheduledJob


class FakeProvider:
    def __init__(self, source: str, listings: list[RawListing] | None = None) -> None:
        self.source = source
        self._listings = listings or []
        self.calls = 0

    async def search(
        self, *, category: OfferCategory, query: str | None = None, limit: int = 20
    ) -> list[RawListing]:
        self.calls += 1
        return self._listings


class FailingProvider:
    source = "broken"

    async def search(
        self, *, category: OfferCategory, query: str | None = None, limit: int = 20
    ) -> list[RawListing]:
        raise RuntimeError("provider is down")


class PassthroughNormalizer:
    def normalize(self, raw: RawListing) -> Offer:
        return Offer(
            id=uuid.uuid4(),
            source=raw.source,
            source_listing_id=raw.source_listing_id,
            title="A valid listing title",
            description="",
            price_amount=100.0,
            price_currency="EUR",
            category=raw.category,
            url=f"https://example.com/{raw.source_listing_id}",
        )


class AcceptEverythingValidator:
    def validate(self, offer: Offer) -> list[str]:
        return []


class _FakeOfferRepository:
    """Replaces `SqlAlchemyOfferRepository` for these tests — records which
    session it was built with (to prove hook_factory got the same one) and
    just appends on `upsert`, skipping real SQL entirely."""

    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def upsert(self, offer: Offer) -> Offer:
        return offer


class _FakeSession:
    def __init__(self, name: str) -> None:
        self.name = name
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _FakeSessionContextManager:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


def _raw(source: OfferSource, listing_id: str) -> RawListing:
    return RawListing(
        source=source,
        source_listing_id=listing_id,
        category=OfferCategory.MACBOOK,
        payload={},
    )


class _RecordingSessionFactory:
    """Hands out a fresh `_FakeSession` per call (mirrors the real
    `async_sessionmaker`: one session per `async with session_factory()`),
    while remembering every session it created for assertions."""

    def __init__(self) -> None:
        self.sessions: list[_FakeSession] = []

    def __call__(self) -> _FakeSessionContextManager:
        session = _FakeSession(name=f"session-{len(self.sessions)}")
        self.sessions.append(session)
        return _FakeSessionContextManager(session)


@pytest.fixture(autouse=True)
def _fake_offer_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler_module, "SqlAlchemyOfferRepository", _FakeOfferRepository)


async def test_run_once_persists_and_commits_a_successful_job() -> None:
    provider = FakeProvider(OfferSource.EBAY.value, [_raw(OfferSource.EBAY, "1")])
    factory = _RecordingSessionFactory()
    scheduler = AsyncIntervalScheduler(
        [ScheduledJob(provider=provider, category=OfferCategory.MACBOOK)],
        session_factory=factory,  # type: ignore[arg-type]
        normalizer=PassthroughNormalizer(),
        validator=AcceptEverythingValidator(),
    )

    await scheduler.run_once()

    assert provider.calls == 1
    assert len(factory.sessions) == 1
    assert factory.sessions[0].committed is True
    assert factory.sessions[0].rolled_back is False


async def test_run_once_builds_the_hook_against_the_jobs_own_session() -> None:
    """The hook must see the *same* session the offer was persisted through
    (see AsyncIntervalScheduler's docstring on `hook_factory`) — otherwise a
    real hook like SavedSearchMatchNotifier couldn't read back the not-yet-
    committed offer it's meant to match against saved searches."""
    provider = FakeProvider(OfferSource.EBAY.value, [_raw(OfferSource.EBAY, "1")])
    factory = _RecordingSessionFactory()
    hook_sessions: list[object] = []
    hooked_offers: list[Offer] = []

    def hook_factory(session: object) -> Callable[[Offer], object]:
        hook_sessions.append(session)

        async def hook(offer: Offer) -> None:
            hooked_offers.append(offer)

        return hook

    scheduler = AsyncIntervalScheduler(
        [ScheduledJob(provider=provider, category=OfferCategory.MACBOOK)],
        session_factory=factory,  # type: ignore[arg-type]
        normalizer=PassthroughNormalizer(),
        validator=AcceptEverythingValidator(),
        hook_factory=hook_factory,  # type: ignore[arg-type]
    )

    await scheduler.run_once()

    assert len(hooked_offers) == 1
    assert hook_sessions == [factory.sessions[0]]


async def test_run_once_without_a_hook_factory_still_persists() -> None:
    provider = FakeProvider(OfferSource.EBAY.value, [_raw(OfferSource.EBAY, "1")])
    factory = _RecordingSessionFactory()
    scheduler = AsyncIntervalScheduler(
        [ScheduledJob(provider=provider, category=OfferCategory.MACBOOK)],
        session_factory=factory,  # type: ignore[arg-type]
        normalizer=PassthroughNormalizer(),
        validator=AcceptEverythingValidator(),
    )

    await scheduler.run_once()  # must not raise

    assert factory.sessions[0].committed is True


async def test_run_once_isolates_one_jobs_failure_from_the_rest() -> None:
    good_provider = FakeProvider(OfferSource.EBAY.value, [_raw(OfferSource.EBAY, "1")])
    jobs = [
        ScheduledJob(provider=FailingProvider(), category=OfferCategory.MACBOOK),
        ScheduledJob(provider=good_provider, category=OfferCategory.MACBOOK),
    ]
    factory = _RecordingSessionFactory()
    scheduler = AsyncIntervalScheduler(
        jobs,
        session_factory=factory,  # type: ignore[arg-type]
        normalizer=PassthroughNormalizer(),
        validator=AcceptEverythingValidator(),
    )

    await scheduler.run_once()  # must not raise despite the first job failing

    assert good_provider.calls == 1
    assert len(factory.sessions) == 2
    assert factory.sessions[0].rolled_back is True  # the failing job's session
    assert factory.sessions[1].committed is True  # the good job's session


async def test_start_then_stop_runs_at_least_once_and_shuts_down_cleanly() -> None:
    provider = FakeProvider(OfferSource.EBAY.value, [])
    factory = _RecordingSessionFactory()
    scheduler = AsyncIntervalScheduler(
        [ScheduledJob(provider=provider, category=OfferCategory.MACBOOK)],
        session_factory=factory,  # type: ignore[arg-type]
        normalizer=PassthroughNormalizer(),
        validator=AcceptEverythingValidator(),
        interval_seconds=1000.0,  # long enough that only stop() ends the loop
    )

    scheduler.start()
    scheduler.start()  # idempotent: must not start a second task

    # `_loop` checks `_stopped.is_set()` *before* its first `run_once()` —
    # calling stop() before the freshly created task has been scheduled at
    # all would set that flag first and skip the run entirely (correct
    # behavior, just not what this test is after) — so yield to the event
    # loop until the task has actually had a turn.
    for _ in range(1000):
        if provider.calls >= 1:
            break
        await asyncio.sleep(0)
    else:
        pytest.fail("scheduler task never ran")

    await scheduler.stop()

    assert provider.calls == 1
