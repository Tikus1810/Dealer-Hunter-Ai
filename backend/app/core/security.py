"""Security primitives: password hashing (Argon2) and JWT access/refresh tokens.

Band 03 requires Argon2 password hashing and JWT access + refresh tokens.
Band 14 requires secure defaults. This module has no framework or database
dependency so it can be unit tested in isolation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import Settings

_password_hasher = PasswordHasher()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, expired, or has the wrong type."""


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id with library-recommended parameters."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2 hash. Never raises on mismatch."""
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the stored hash was created with outdated Argon2 parameters."""
    return _password_hasher.check_needs_rehash(password_hash)


def create_token(
    *,
    subject: str,
    token_type: TokenType,
    settings: Settings,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT for `subject` (the user id).

    Access tokens are short-lived; refresh tokens are long-lived and only
    valid for obtaining new access tokens (enforced via the `type` claim).
    """
    now = datetime.now(UTC)
    if token_type is TokenType.ACCESS:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    else:
        expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded: str = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded


def decode_token(token: str, *, settings: Settings, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a JWT, enforcing the expected token type.

    Raises InvalidTokenError for any malformed, expired, or wrong-type token.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"expected token type '{expected_type.value}'")

    return payload
