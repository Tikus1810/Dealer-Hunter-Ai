"""Pydantic v2 DTOs for the users API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    is_active: bool
    roles: list[str]


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
