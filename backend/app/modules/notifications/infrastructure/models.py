"""SQLAlchemy model for the `notifications` module (Band 09/11)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.notifications.domain.entities import NotificationChannel, NotificationEvent


class NotificationModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[NotificationEvent] = mapped_column(
        Enum(NotificationEvent, native_enum=False, length=40, validate_strings=True), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, native_enum=False, length=20, validate_strings=True),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
