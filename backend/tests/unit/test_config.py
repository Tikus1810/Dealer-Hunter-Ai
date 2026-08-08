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
    # Explicit, not a bare `Settings()`: pydantic-settings reads
    # JWT_SECRET_KEY from the real process environment when the field
    # isn't passed to the constructor, and CI's own `backend` job sets
    # JWT_SECRET_KEY=ci-test-secret for the *other* tests that need a real
    # value (see .github/workflows/ci.yml) — a bare `Settings()` here
    # would silently pick that up instead of the code default and this
    # assertion would fail in CI while passing locally, which is exactly
    # what happened the first time this test was written.
    assert Settings(jwt_secret_key=INSECURE_DEFAULT_JWT_SECRET_KEY).has_insecure_jwt_secret is True


def test_has_insecure_jwt_secret_false_once_overridden() -> None:
    assert Settings(jwt_secret_key="a-real-generated-secret").has_insecure_jwt_secret is False


def test_assert_safe_for_environment_raises_for_production_with_default_secret() -> None:
    # jwt_secret_key passed explicitly — see the comment on
    # test_has_insecure_jwt_secret_true_for_unconfigured_default above for
    # why relying on the constructor's own fallback isn't safe here.
    settings = Settings(app_env="production", jwt_secret_key=INSECURE_DEFAULT_JWT_SECRET_KEY)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        assert_safe_for_environment(settings)


def test_assert_safe_for_environment_allows_production_with_a_real_secret() -> None:
    settings = Settings(app_env="production", jwt_secret_key="a-real-generated-secret")

    assert_safe_for_environment(settings)  # must not raise


def test_assert_safe_for_environment_allows_development_with_the_default_secret() -> None:
    settings = Settings(app_env="development")

    assert_safe_for_environment(settings)  # must not raise — that's what dev is for


def test_rate_limiting_looks_unsafe_for_production_true_when_disabled_in_prod() -> None:
    settings = Settings(app_env="production", rate_limit_enabled=False)
    assert settings.rate_limiting_looks_unsafe_for_production is True


def test_rate_limiting_looks_unsafe_for_production_false_when_enabled() -> None:
    settings = Settings(app_env="production", rate_limit_enabled=True)
    assert settings.rate_limiting_looks_unsafe_for_production is False


def test_rate_limiting_looks_unsafe_for_production_false_outside_production() -> None:
    # Off-by-default in dev/test is expected and fine (app/core/rate_limit.py) —
    # only production without it is the signal worth surfacing.
    settings = Settings(app_env="development", rate_limit_enabled=False)
    assert settings.rate_limiting_looks_unsafe_for_production is False
