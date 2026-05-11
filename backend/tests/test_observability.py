"""Tests for Sentry init opt-in behavior."""
from __future__ import annotations

from unittest.mock import patch

from aegis.config import Settings
from aegis.observability import init_sentry


def test_init_sentry_skipped_when_dsn_empty():
    s = Settings(sentry_dsn="", _env_file=None)
    with patch("sentry_sdk.init") as mock_init:
        init_sentry(s)
    mock_init.assert_not_called()


def test_init_sentry_called_when_dsn_set():
    s = Settings(sentry_dsn="https://public@test.ingest.sentry.io/1", env="test", _env_file=None)
    with patch("sentry_sdk.init") as mock_init:
        init_sentry(s)
    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == "https://public@test.ingest.sentry.io/1"
    assert kwargs["environment"] == "test"
    assert kwargs["send_default_pii"] is False
