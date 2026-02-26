"""Unit tests for environment config loading."""

import os
import unittest
from unittest.mock import patch

from atlassian_mcp_server.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_success(self) -> None:
        env = {
            "ATLASSIAN_BASE_URL": "https://example.atlassian.net/",
            "ATLASSIAN_EMAIL": "user@example.com",
            "ATLASSIAN_API_TOKEN": "token",
            "ATLASSIAN_TIMEOUT_SECONDS": "15",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_config()

        self.assertEqual(config.normalized_base_url, "https://example.atlassian.net")
        self.assertEqual(config.timeout_seconds, 15.0)

    def test_load_config_missing_required(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError):
                load_config()


if __name__ == "__main__":
    unittest.main()
