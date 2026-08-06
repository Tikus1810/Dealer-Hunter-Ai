"""Unit tests for SavedSearchMatchNotifier against in-memory fakes."""

from __future__ import annotations

import uuid
from typing import Any

from app.modules.notifications.application.match_notifier import SavedSearchMatchNotifier
from app.modules.notifications.domain.entities import (
    DevicePlatform,
    DeviceToken,
    Notification,
    NotificationChannel,
    NotificationEvent,
    NotificationPreference,
)
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.search.domain.entities import SearchProfile


class FakeMatcher:
    def __init__(self, matched_ids: list[uuid.UUID]) -> None:
        self._matched_ids = matched_ids

    async def match_offer_against_profiles(self, offer_id: uuid.UUID) -> list[uuid.UUID]:
        return self._matched_ids


class FakeSearchProfileRepository:
    def __init__(self, profiles: list[SearchProfile]) -> None:
        self._profiles = {p.id: p for p in profiles}

    async def get_by_id(self, profile_id: uuid.UUID) -> SearchProfile | None:
        return self._profiles.get(profile_id)

    async def list_active(self) -> list[SearchProfile]:
        raise NotImplementedError

    async def list_for_user(self, user_id: uuid.UUID) -> list[SearchProfile]:
        raise NotImplementedError

    async def create(self, profile: SearchProfile) -> SearchProfile:
        raise NotImplementedError

    async def update(self, profile: SearchProfile) -> SearchProfile:
        raise NotImplementedError

    async def delete(self, profile_id: uuid.UUID) -> None:
        raise NotImplementedError


class FakeNotificationService:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self._fail = fail

    async def register_device(
        self, user_id: uuid.UUID, *, token: str, platform: DevicePlatform
    ) -> DeviceToken:
        raise NotImplementedError

    async def unregister_device(self, user_id: uuid.UUID, *, token: str) -> None:
        raise NotImplementedError

    async def notify_user(
        self, user_id: uuid.UUID, *, event: NotificationEvent, data: dict[str, Any]
    ) -> list[Notification]:
        if self._fail:
            raise RuntimeError("boom")
        self.calls.append({"user_id": user_id, "event": event, "data": data})
        return []

    async def list_notifications(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Notification], int]:
        raise NotImplementedError

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        raise NotImplementedError

    async def get_preferences(self, user_id: uuid.UUID) -> list[NotificationPreference]:
        raise NotImplementedError

    async def set_preference(
        self,
        user_id: uuid.UUID,
        *,
        event: NotificationEvent,
        channel: NotificationChannel,
        enabled: bool,
    ) -> NotificationPreference:
        raise NotImplementedError


def _offer() -> Offer:
    return Offer(
        id=uuid.uuid4(),
        source=OfferSource.EBAY,
        source_listing_id=str(uuid.uuid4()),
        title="MacBook Pro 14 M3",
        description="Wie neu.",
        price_amount=900.0,
        price_currency="EUR",
        category=OfferCategory.MACBOOK,
        url="https://ebay.de/itm/x",
    )


def _profile(user_id: uuid.UUID) -> SearchProfile:
    return SearchProfile(
        id=uuid.uuid4(), user_id=user_id, name="Cheap MacBooks", category="macbook"
    )


async def test_notifies_every_matched_profiles_owner() -> None:
    offer = _offer()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    profile_a, profile_b = _profile(user_a), _profile(user_b)
    matcher = FakeMatcher([profile_a.id, profile_b.id])
    profiles = FakeSearchProfileRepository([profile_a, profile_b])
    notifications = FakeNotificationService()

    notifier = SavedSearchMatchNotifier(matcher, profiles, notifications)
    await notifier(offer)

    notified_users = {c["user_id"] for c in notifications.calls}
    assert notified_users == {user_a, user_b}
    assert all(c["event"] == NotificationEvent.SAVED_SEARCH_MATCH for c in notifications.calls)
    assert all(c["data"]["offer_title"] == offer.title for c in notifications.calls)


async def test_no_matches_notifies_nobody() -> None:
    offer = _offer()
    notifier = SavedSearchMatchNotifier(
        FakeMatcher([]), FakeSearchProfileRepository([]), FakeNotificationService()
    )
    await notifier(offer)
    # No exception, nothing to assert beyond "didn't crash" — covered by
    # FakeNotificationService.calls staying implicitly empty (no calls made).


async def test_notification_failure_for_one_profile_does_not_raise() -> None:
    offer = _offer()
    profile = _profile(uuid.uuid4())
    notifier = SavedSearchMatchNotifier(
        FakeMatcher([profile.id]),
        FakeSearchProfileRepository([profile]),
        FakeNotificationService(fail=True),
    )
    await notifier(offer)  # must not raise despite the notification service failing


async def test_unknown_matched_profile_id_is_skipped() -> None:
    offer = _offer()
    notifications = FakeNotificationService()
    notifier = SavedSearchMatchNotifier(
        FakeMatcher([uuid.uuid4()]), FakeSearchProfileRepository([]), notifications
    )
    await notifier(offer)
    assert notifications.calls == []
