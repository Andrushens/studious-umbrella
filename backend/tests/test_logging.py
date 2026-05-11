"""Tests for aegis.logging configuration."""
from __future__ import annotations

import json
import logging

import structlog

from aegis.logging import configure_logging


def test_configure_logging_json_emits_parseable_line(capfd):
    configure_logging(level="INFO", fmt="json")
    log = structlog.get_logger("aegis.test")
    log.info("test_event", foo="bar")

    captured = capfd.readouterr()
    blob = captured.err or captured.out
    line = next(line for line in blob.splitlines() if "test_event" in line)
    parsed = json.loads(line)
    assert parsed["event"] == "test_event"
    assert parsed["foo"] == "bar"
    assert parsed["level"] == "info"


def test_configure_logging_console_does_not_crash(capfd):
    configure_logging(level="DEBUG", fmt="console")
    log = structlog.get_logger("aegis.test")
    log.warning("console_event", x=1)
    captured = capfd.readouterr()
    assert "console_event" in (captured.err + captured.out)


def test_configure_logging_routes_stdlib_through_structlog(capfd):
    configure_logging(level="INFO", fmt="json")
    logging.getLogger("uvicorn.error").info("stdlib_hello")
    captured = capfd.readouterr()
    blob = captured.err or captured.out
    assert "stdlib_hello" in blob
