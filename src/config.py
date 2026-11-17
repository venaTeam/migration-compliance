"""Application configuration."""

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COMPLIANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    port: int = 8000
    log_level: str = "info"
    # Accept both JSON arrays and comma-separated strings. The validator below
    # always normalises this to a list[str].
    cors_allowed_origins: str | list[str] = "http://localhost:5173,http://localhost:3000"

    # Default Grafana URL used only when not overridden by the request.
    grafana_url: str = "https://grafana-development.d8200.mil"

    # Allow HTTPS requests to Grafana instances with self-signed certificates.
    grafana_insecure_tls: bool = False

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_allowed_origins(cls, value: object) -> list[str]:
        """Accept both JSON arrays and comma-separated origin lists."""
        if isinstance(value, list):
            return [str(item) for item in value]
        if not isinstance(value, str):
            return ["http://localhost:5173", "http://localhost:3000"]
        value = value.strip()
        if not value:
            return ["http://localhost:5173", "http://localhost:3000"]
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            pass
        return [origin.strip() for origin in value.split(",") if origin.strip()]


settings = Settings()
