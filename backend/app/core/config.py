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
    jwt_secret_key: str = Field(default="dev-only-insecure-secret-change-me")
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

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (safe: settings are immutable per process)."""
    return Settings()
