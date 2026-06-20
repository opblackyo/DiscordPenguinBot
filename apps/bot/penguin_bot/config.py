"""Environment-backed configuration for the bot runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when configuration is invalid for the requested runtime."""


def _optional_value(environment: Mapping[str, str], key: str) -> str | None:
    value = environment.get(key, "").strip()
    return value or None


def _optional_int(environment: Mapping[str, str], key: str) -> int | None:
    value = _optional_value(environment, key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as error:
        raise ConfigurationError(f"{key} must be an integer.") from error


def _port(environment: Mapping[str, str]) -> int:
    value = environment.get("LAVALINK_PORT", "2333")
    try:
        return int(value)
    except ValueError as error:
        raise ConfigurationError("LAVALINK_PORT must be an integer.") from error


def _bool(environment: Mapping[str, str], key: str, default: bool = False) -> bool:
    value = _optional_value(environment, key)
    if value is None:
        return default
    if value.lower() in {"1", "true", "yes", "on"}:
        return True
    if value.lower() in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{key} must be a boolean.")


@dataclass(frozen=True)
class Settings:
    """All external configuration. Secrets are never logged or returned."""

    discord_token: str | None
    discord_client_id: int | None
    discord_guild_id: int | None
    lavalink_host: str
    lavalink_port: int
    lavalink_password: str | None
    lavalink_secure: bool
    ai_base_url: str | None
    ai_api_key: str | None
    ai_model: str | None
    dashboard_secret: str | None
    database_url: str
    music_status_snapshot_path: str | None

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "Settings":
        if environment is None:
            load_dotenv()
            environment = os.environ

        return cls(
            discord_token=_optional_value(environment, "DISCORD_TOKEN"),
            discord_client_id=_optional_int(environment, "DISCORD_CLIENT_ID"),
            discord_guild_id=_optional_int(environment, "DISCORD_GUILD_ID"),
            lavalink_host=environment.get("LAVALINK_HOST", "lavalink"),
            lavalink_port=_port(environment),
            lavalink_password=_optional_value(environment, "LAVALINK_PASSWORD"),
            lavalink_secure=_bool(environment, "LAVALINK_SECURE"),
            ai_base_url=_optional_value(environment, "AI_BASE_URL"),
            ai_api_key=_optional_value(environment, "AI_API_KEY"),
            ai_model=_optional_value(environment, "AI_MODEL"),
            dashboard_secret=_optional_value(environment, "DASHBOARD_SECRET"),
            database_url=environment.get("DATABASE_URL", "sqlite:///data/db/discord_penguin.db"),
            music_status_snapshot_path=_optional_value(environment, "MUSIC_STATUS_SNAPSHOT_PATH"),
        )

    def require_discord_token(self) -> str:
        if self.discord_token is None:
            raise ConfigurationError("DISCORD_TOKEN is required to start the bot.")
        return self.discord_token

    def safe_status(self) -> dict[str, object]:
        """Return only non-secret configuration facts for logs and diagnostics."""

        return {
            "discord_token_configured": self.discord_token is not None,
            "discord_client_id_configured": self.discord_client_id is not None,
            "discord_guild_id_configured": self.discord_guild_id is not None,
            "lavalink_host": self.lavalink_host,
            "lavalink_port": self.lavalink_port,
            "lavalink_password_configured": self.lavalink_password is not None,
            "lavalink_secure": self.lavalink_secure,
            "ai_configured": all((self.ai_base_url, self.ai_api_key, self.ai_model)),
            "dashboard_secret_configured": self.dashboard_secret is not None,
            "database_url_configured": bool(self.database_url),
            "music_status_snapshot_configured": self.music_status_snapshot_path is not None,
        }
