"""Configuration loading for Atlassian MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when required configuration values are missing."""


@dataclass(frozen=True)
class AtlassianConfig:
    """Environment-driven configuration for Atlassian Cloud APIs."""

    base_url: str
    email: str
    api_token: str
    timeout_seconds: float = 30.0

    @property
    def normalized_base_url(self) -> str:
        """Return base URL without trailing slash."""
        return self.base_url.rstrip("/")


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def load_config() -> AtlassianConfig:
    """Load configuration from environment variables."""
    timeout = os.getenv("ATLASSIAN_TIMEOUT_SECONDS", "30").strip()
    try:
        timeout_seconds = float(timeout)
    except ValueError as exc:
        raise ConfigError("ATLASSIAN_TIMEOUT_SECONDS must be numeric") from exc

    return AtlassianConfig(
        base_url=_require_env("ATLASSIAN_BASE_URL"),
        email=_require_env("ATLASSIAN_EMAIL"),
        api_token=_require_env("ATLASSIAN_API_TOKEN"),
        timeout_seconds=timeout_seconds,
    )
