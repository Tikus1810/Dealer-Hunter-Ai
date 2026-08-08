"""Application configuration.

Central, typed settings object loaded from environment variables / .env.
Nothing in this module may depend on FastAPI, SQLAlchemy sessions, or any
other infrastructure detail beyond `pydantic-settings` itself, so it stays
safe to import from every layer (Band 02: layering rule).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Named so `Settings.has_insecure_jwt_secret` can compare against it without
# duplicating the literal — see that property's docstring.
INSECURE_DEFAULT_JWT_SECRET_KEY = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=False)
    app_name: str = Field(default="Deal Hunter AI")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://dealhunter:dealhunter@localhost:5432/dealhunter"
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://dealhunter:dealhunter@localhost:5432/dealhunter"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # JWT
    jwt_secret_key: str = Field(default=INSECURE_DEFAULT_JWT_SECRET_KEY)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=15)
    jwt_refresh_token_expire_days: int = Field(default=30)

    # CORS
    cors_allowed_origins: str = Field(default="http://localhost:3000")

    # eBay official API
    ebay_client_id: str = Field(default="")
    ebay_client_secret: str = Field(default="")
    ebay_env: str = Field(default="PRODUCTION")

    # eBay Kleinanzeigen provider
    kleinanzeigen_provider_enabled: bool = Field(default=False)
    kleinanzeigen_request_delay_seconds: float = Field(default=3.0)

    # Firebase Cloud Messaging
    fcm_project_id: str = Field(default="")
    fcm_credentials_json_path: str = Field(default="")

    # Claude Vision API (Band 08: cosmetic-condition detection)
    # Optional — cosmetic_condition stays "not_available" until this is set.
    anthropic_api_key: str = Field(default="")
    anthropic_vision_model: str = Field(default="claude-opus-5")

    # Marketplace ingestion scheduler (Band 13: Deployment/DevOps).
    # Off by default so every non-production run (tests, local `uvicorn`
    # without a filled-in .env) doesn't silently start background network
    # calls against eBay. Production deployments opt in explicitly.
    scheduler_enabled: bool = Field(default=False)
    scheduler_interval_seconds: float = Field(default=900.0)

    # Rate limiting (Band 14: Security-Härtung). Off by default — see
    # app/core/rate_limit.py's module docstring for why default-on would
    # break the existing integration test suite.
    rate_limit_enabled: bool = Field(default=False)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def has_insecure_jwt_secret(self) -> bool:
        """True if `JWT_SECRET_KEY` was never overridden from its
        development-only default. That default is a public string
        (committed to this file, visible in `docs/deployment.md`, and now
        in this repo's public GitHub history) — anyone who has read it can
        forge a valid access token for any user id. Fine in development,
        a critical vulnerability if it ever reached production, which is
        exactly what `assert_safe_for_environment` below exists to catch
        before the app ever accepts a request."""
        return self.jwt_secret_key == INSECURE_DEFAULT_JWT_SECRET_KEY


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (safe: settings are immutable per process)."""
    return Settings()


def assert_safe_for_environment(settings: Settings) -> None:
    """Refuse to start if `settings` would run a production deployment with
    secrets that were never actually configured (Band 14: Security-Härtung
    — "fail loud, not silent", the same principle
    `infra/docker/docker-compose.prod.yml`'s `${VAR:?error message}` guards
    already apply at the container level, now also enforced at the
    application level so a misconfigured non-Docker deployment — e.g. a
    bare `uvicorn` process with `APP_ENV=production` but no `.env` —
    can't silently boot insecure).

    Called once from `app.main.lifespan` on startup, not at import time
    (`Settings()`/`get_settings()` must stay side-effect-free so every
    other module can import `app.core.config` freely — Band 02's
    layering rule)."""
    if settings.is_production and settings.has_insecure_jwt_secret:
        raise RuntimeError(
            "Refusing to start: APP_ENV=production but JWT_SECRET_KEY is "
            "still the insecure development default. Set a real "
            'JWT_SECRET_KEY (e.g. `python -c "import secrets; '
            'print(secrets.token_urlsafe(64))"`) before deploying.'
        )
