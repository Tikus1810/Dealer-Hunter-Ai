"""Shared invariant checks for AI-produced values (Band 16: AI Rules —
"validation rules"). Every score/confidence value this codebase produces
(DealBrain, RepairBrain, Vision AI) must fall within its documented range
— `ScoringEngine`/`RepairScoringEngine` already clamp on the way out, but
clamping-at-the-source only protects values built through that one code
path. These are called from each entity's `__post_init__` instead, so the
invariant holds no matter how the entity gets constructed (a future
analyzer, a test double, a bug) — the entity itself refuses to exist in an
invalid state, rather than trusting every producer to have clamped
correctly.

Raises plain `ValueError`, not a `DomainError` subclass: this is a
programming-invariant check on a domain entity's own construction, not a
user-facing request validation (that's `app.core.exceptions.ValidationError`,
raised by application-layer code reacting to *input*). A `ValueError` here
means a bug in this codebase, not a bad request — it should fail loudly in
tests/dev, not become a formatted 4xx API response.
"""

from __future__ import annotations


def validate_score(name: str, value: int, *, min_value: int = 0, max_value: int = 100) -> None:
    if not (min_value <= value <= max_value):
        raise ValueError(f"{name} must be between {min_value} and {max_value}, got {value}")


def validate_confidence(name: str, value: float) -> None:
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")
