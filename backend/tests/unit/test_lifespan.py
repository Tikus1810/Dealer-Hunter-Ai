"""Unit tests for app.main.lifespan's startup guards (Band 14).

Exercises `lifespan` directly as an async context manager rather than only
`app.core.config`'s pure functions in isolation — those are unit-tested on
their own in `test_config.py`, but `lifespan` is the only thing that
actually *calls* `assert_safe_for_environment` on a real app boot, and
nothing else in this suite drives it (the integration suite's
`ASGITransport(app=app)` clients never run `lifespan`, by design — httpx
doesn't unless wrapped in an explicit lifespan manager). Monkeypatches
`get_settings` so no real scheduler/DB/Redis is touched — `scheduler_
enabled=False` (the default) already makes `build_scheduler` a no-op, but
patching keeps this test independent of that default ever changing.
"""

from __future__ import annotations

import pytest

from app import main as main_module
from app.core.config import Settings
from app.main import app, lifespan


async def test_lifespan_raises_for_production_with_insecure_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(app_env="production")  # default jwt_secret_key = insecure default
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        async with lifespan(app):
            pass


async def test_lifespan_starts_cleanly_for_production_with_a_real_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(app_env="production", jwt_secret_key="a-real-generated-secret")
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    async with lifespan(app):
        pass  # must not raise


async def test_lifespan_starts_cleanly_for_development_with_the_default_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(app_env="development")
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    async with lifespan(app):
        pass  # must not raise — the insecure default is expected in dev
