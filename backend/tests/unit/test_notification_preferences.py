"""Unit tests for PreferenceResolver — pure, no I/O."""

from __future__ import annotations

import uuid

from app.modules.notifications.domain.entities import (
    NotificationChannel,
    NotificationEvent,
    NotificationPreference,
)
from app.modules.notifications.domain.preferences import PreferenceResolver


def test_no_preference_recorded_defaults_to_enabled() -> None:
    enabled = PreferenceResolver.is_enabled(
        [], event=NotificationEvent.SAVED_SEARCH_MATCH, channel=NotificationChannel.PUSH
    )
    assert enabled is True


def test_explicit_disabled_preference_is_respected() -> None:
    user_id = uuid.uuid4()
    preferences = [
        NotificationPreference(
            user_id=user_id,
            event=NotificationEvent.SAVED_SEARCH_MATCH,
            channel=NotificationChannel.PUSH,
            enabled=False,
        )
    ]
    enabled = PreferenceResolver.is_enabled(
        preferences, event=NotificationEvent.SAVED_SEARCH_MATCH, channel=NotificationChannel.PUSH
    )
    assert enabled is False


def test_preference_for_a_different_channel_does_not_apply() -> None:
    user_id = uuid.uuid4()
    preferences = [
        NotificationPreference(
            user_id=user_id,
            event=NotificationEvent.SAVED_SEARCH_MATCH,
            channel=NotificationChannel.PUSH,
            enabled=False,
        )
    ]
    enabled = PreferenceResolver.is_enabled(
        preferences, event=NotificationEvent.SAVED_SEARCH_MATCH, channel=NotificationChannel.EMAIL
    )
    assert enabled is True
