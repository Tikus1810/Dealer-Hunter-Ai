"""Unit tests for app.core.security — no DB, no network."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_verifiable_hash() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret_key="test-secret", jwt_algorithm="HS256")


def test_access_token_round_trip(settings: Settings) -> None:
    token = create_token(subject="user-123", token_type=TokenType.ACCESS, settings=settings)
    payload = decode_token(token, settings=settings, expected_type=TokenType.ACCESS)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_refresh_token_rejected_as_access_token(settings: Settings) -> None:
    token = create_token(subject="user-123", token_type=TokenType.REFRESH, settings=settings)
    with pytest.raises(InvalidTokenError):
        decode_token(token, settings=settings, expected_type=TokenType.ACCESS)


def test_tampered_token_is_rejected(settings: Settings) -> None:
    token = create_token(subject="user-123", token_type=TokenType.ACCESS, settings=settings)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(InvalidTokenError):
        decode_token(tampered, settings=settings, expected_type=TokenType.ACCESS)
