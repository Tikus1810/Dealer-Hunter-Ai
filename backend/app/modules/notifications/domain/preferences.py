"""Preference resolution (Band 11: notification preferences, user opt-in/
out). Opt-out model: every (event, channel) is enabled by default, so a
user only ever needs a row for the things they've turned *off*.
"""

from __future__ import annotations

from app.modules.notifications.domain.entities import (
    NotificationChannel,
    NotificationEvent,
    NotificationPreference,
)


class PreferenceResolver:
    @staticmethod
    def is_enabled(
        preferences: list[NotificationPreference],
        *,
        event: NotificationEvent,
        channel: NotificationChannel,
    ) -> bool:
        for pref in preferences:
            if pref.event == event and pref.channel == channel:
                return pref.enabled
        return True  # no explicit preference recorded => enabled
