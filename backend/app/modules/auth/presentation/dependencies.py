"""FastAPI dependency for extracting and validating the authenticated user.

Reused by every protected route across modules — this is the auth module's
public surface for the rest of the presentation layer (Band 02: modules
expose interfaces only).
"""

from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import InvalidTokenError, TokenType, decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> uuid.UUID:
    if credentials is None:
        raise UnauthorizedError("missing bearer token")
    try:
        payload = decode_token(
            credentials.credentials, settings=settings, expected_type=TokenType.ACCESS
        )
    except InvalidTokenError as exc:
        raise UnauthorizedError("invalid or expired access token") from exc

    return uuid.UUID(payload["sub"])
