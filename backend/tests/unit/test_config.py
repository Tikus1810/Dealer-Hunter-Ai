"""Unit tests for app.core.config.Settings' derived properties — no I/O."""

from __future__ import annotations

import pytest

from app.core.config import (
    INSECURE_DEFAULT_JWT_SECRET_KEY,
    Settings,
    assert_safe_for_environment,
)


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


def test_has_insecure_jwt_secret_true_for_unconfigured_default() -> None:
    assert Settings().has_insecure_jwt_secret is True
    assert Settings(jwt_secret_key=INSECURE_DEFAULT_JWT_SECRET_KEY).has_insecure_jwt_secret is True


def test_has_insecure_jwt_secret_false_once_overridden() -> None:
    assert Settings(jwt_secret_key="a-real-generated-secret").has_insecure_jwt_secret is False


def test_assert_safe_for_environment_raises_for_production_with_default_secret() -> None:
    settings = Settings(app_env="production")

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        assert_safe_for_environment(settings)


def test_assert_safe_for_environment_allows_production_with_a_real_secret() -> None:
    settings = Settings(app_env="production", jwt_secret_key="a-real-generated-secret")

    assert_safe_for_environment(settings)  # must not raise


def test_assert_safe_for_environment_allows_development_with_the_default_secret() -> None:
    settings = Settings(app_env="development")

    assert_safe_for_environment(settings)  # must not raise — that's what dev is for
