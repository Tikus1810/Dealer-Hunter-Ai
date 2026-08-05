"""Users domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class User:
    id: uuid.UUID
    email: str
    password_hash: str
    display_name: str | None = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    roles: list[str] = field(default_factory=lambda: ["user"])
