"""Tests for aegis.config.Settings."""
from __future__ import annotations

import pytest

from aegis.config import Settings


def test_defaults_applied(monkeypatch):
    for var in (
        "DATABASE_URL",
        "ETHERSCAN_API_KEY",
        "ALCHEMY_API_KEY",
        "LOG_LEVEL",
        "LOG_FORMAT",
        "SCHEDULER_ENABLED",
        "SCAN_INTERVAL_MINUTES",
        "SCAN_CONCURRENCY",
        "HTTP_TIMEOUT_SECONDS",
        "SENTRY_DSN",
        "ENV",
    ):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.database_url == "sqlite+aiosqlite:///./aegis.db"
    assert s.etherscan_api_key == ""
    assert s.alchemy_api_key == ""
    assert s.log_level == "INFO"
    assert s.log_format == "console"
    assert s.scheduler_enabled is True
    assert s.scan_interval_minutes == 60
    assert s.scan_concurrency == 4
    assert s.http_timeout_seconds == pytest.approx(10.0)
    assert s.sentry_dsn == ""
    assert s.env == "development"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("ETHERSCAN_API_KEY", "abc123")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("SCAN_INTERVAL_MINUTES", "5")
    monkeypatch.setenv("LOG_FORMAT", "json")
    s = Settings(_env_file=None)
    assert s.etherscan_api_key == "abc123"
    assert s.scheduler_enabled is False
    assert s.scan_interval_minutes == 5
    assert s.log_format == "json"


def test_constructor_kwargs_override(monkeypatch):
    monkeypatch.delenv("ETHERSCAN_API_KEY", raising=False)
    s = Settings(etherscan_api_key="kwarg-key", _env_file=None)
    assert s.etherscan_api_key == "kwarg-key"
