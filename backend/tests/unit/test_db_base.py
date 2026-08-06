"""Unit tests for app.db.base mixins — pure Python, no DB connection
needed (SQLAlchemy declarative attributes work as plain instance
attributes off a live session)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.db.base import SoftDeleteMixin


class _SoftDeletable(SoftDeleteMixin):
    """A bare mixin consumer — real models add `Base`/`UUIDPrimaryKeyMixin`
    too, but `is_deleted` only touches `deleted_at`."""

    def __init__(self, deleted_at: datetime | None = None) -> None:
        self.deleted_at = deleted_at


def test_is_deleted_false_when_deleted_at_is_none() -> None:
    assert _SoftDeletable(deleted_at=None).is_deleted is False


def test_is_deleted_true_when_deleted_at_is_set() -> None:
    assert _SoftDeletable(deleted_at=datetime.now(UTC)).is_deleted is True
