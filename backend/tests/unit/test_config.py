"""Unit tests for app.core.config.Settings' derived properties — no I/O."""

from __future__ import annotations

from app.core.config import Settings


def test_cors_origins_list_splits_and_strips() -> None:
    settings = Settings(cors_allowed_origins=" http://a.com ,http://b.com,,http://c.com ")
    assert settings.cors_origins_list == ["http://a.com", "http://b.com", "http://c.com"]


def test_cors_origins_list_empty_string_yields_empty_list() -> None:
    settings = Settings(cors_allowed_origins="")
    assert settings.cors_origins_list == []


def test_is_production_true_for_production_env_case_insensitive() -> None:
    assert Settings(app_env="production").is_production is True
    assert Settings(app_env="PRODUCTION").is_production is True


def test_is_production_false_for_development_env() -> None:
    assert Settings(app_env="development").is_production is False
