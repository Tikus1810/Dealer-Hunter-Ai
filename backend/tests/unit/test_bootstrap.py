"""Unit tests for app.bootstrap.build_scheduler — the Task #14 composition
root that finally gives AsyncIntervalScheduler (built in Task #5, unused
until now) a real call site. Provider classes are monkeypatched out so this
never touches the network or needs real eBay/Kleinanzeigen credentials.
"""

from __future__ import annotations

import pytest

from app import bootstrap
from app.core.config import Settings
from app.modules.notifications.application.match_notifier import SavedSearchMatchNotifier
from app.modules.offers.infrastructure.scheduler import AsyncIntervalScheduler


class _FakeProvider:
    def __init__(self, settings: object) -> None:
        self.settings = settings


class _FakeSession:
    """Stand-in for AsyncSession: every repository this module builds just
    stores it (`self._session = session`), no attribute access at
    construction time — see e.g. SqlAlchemySearchProfileRepository."""


def test_build_scheduler_returns_none_when_disabled() -> None:
    settings = Settings(scheduler_enabled=False)
    assert bootstrap.build_scheduler(settings) is None


def test_build_scheduler_returns_none_when_enabled_but_no_provider_configured() -> None:
    settings = Settings(
        scheduler_enabled=True,
        ebay_client_id="",
        ebay_client_secret="",
        kleinanzeigen_provider_enabled=False,
    )
    assert bootstrap.build_scheduler(settings) is None


def test_build_scheduler_builds_one_job_per_category_when_ebay_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "EbayApiProvider", _FakeProvider)
    settings = Settings(scheduler_enabled=True, ebay_client_id="id", ebay_client_secret="secret")

    scheduler = bootstrap.build_scheduler(settings)

    assert isinstance(scheduler, AsyncIntervalScheduler)
    assert len(scheduler._jobs) == len(bootstrap._ALL_CATEGORIES)


def test_build_scheduler_adds_kleinanzeigen_jobs_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "EbayApiProvider", _FakeProvider)
    monkeypatch.setattr(bootstrap, "KleinanzeigenProvider", _FakeProvider)
    settings = Settings(
        scheduler_enabled=True,
        ebay_client_id="id",
        ebay_client_secret="secret",
        kleinanzeigen_provider_enabled=True,
    )

    scheduler = bootstrap.build_scheduler(settings)

    assert isinstance(scheduler, AsyncIntervalScheduler)
    assert len(scheduler._jobs) == len(bootstrap._ALL_CATEGORIES) * 2


def test_build_scheduler_uses_the_configured_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "EbayApiProvider", _FakeProvider)
    settings = Settings(
        scheduler_enabled=True,
        ebay_client_id="id",
        ebay_client_secret="secret",
        scheduler_interval_seconds=42.0,
    )

    scheduler = bootstrap.build_scheduler(settings)

    assert isinstance(scheduler, AsyncIntervalScheduler)
    assert scheduler._interval == 42.0


def test_hook_factory_builds_a_saved_search_match_notifier_bound_to_the_session() -> None:
    factory = bootstrap._build_hook_factory(Settings())

    hook = factory(_FakeSession())  # type: ignore[arg-type]

    assert isinstance(hook, SavedSearchMatchNotifier)
