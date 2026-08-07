"""Event taxonomy + validation rules (Band 15: "event taxonomy", "privacy",
"validation rules"). Pure, no I/O — `AnalyticsService` is the only caller.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Final

MAX_EVENT_NAME_LENGTH: Final = 120  # matches AnalyticsEventModel.name's column width
MAX_PROPERTY_COUNT: Final = 25
MAX_PROPERTY_KEY_LENGTH: Final = 60
MAX_PROPERTY_STRING_VALUE_LENGTH: Final = 500

# snake_case only (Band 15: taxonomy) — keeps event names queryable/
# groupable without a normalization pass, and rules out anyone using this
# field as a free-text log line.
_EVENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,119}$")

# Defense-in-depth, not exhaustive (Band 15: privacy) — analytics
# properties are meant for behavioral facts ("category": "macbook"), never
# credentials or contact details. This catches the obvious mistakes; it is
# not a substitute for the client (Flutter app) simply never sending PII
# here in the first place — see docs/analytics.md's "Privacy" section.
DENYLISTED_PROPERTY_KEYS: Final = frozenset(
    {
        "password",
        "password_hash",
        "email",
        "phone",
        "phone_number",
        "ssn",
        "credit_card",
        "card_number",
        "cvv",
        "access_token",
        "refresh_token",
        "jwt",
        "authorization",
    }
)


class AnalyticsEventName(StrEnum):
    """Known, first-party event names this backend emits automatically
    (see AuthService/FavoriteService). Not an exhaustive allowlist — the
    track endpoint also accepts client-driven event names (e.g. Flutter
    screen views) that aren't enumerated here, validated only against the
    shape rules above, not against this enum. This exists so the handful
    of events this codebase itself emits have one canonical spelling
    instead of being string literals scattered across modules."""

    USER_REGISTERED = "user_registered"
    OFFER_FAVORITED = "offer_favorited"
    OFFER_UNFAVORITED = "offer_unfavorited"


def is_valid_event_name(name: str) -> bool:
    return bool(_EVENT_NAME_PATTERN.match(name))
