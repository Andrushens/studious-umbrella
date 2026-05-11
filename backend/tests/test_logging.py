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
    blob = captured.err + captured.out
    line = next(
        (line for line in blob.splitlines() if "test_event" in line), None
    )
    assert line is not None, f"test_event not found in output: {blob!r}"
    parsed = json.loads(line)
    assert parsed["event"] == "test_event"
    assert parsed["foo"] == "bar"
    assert parsed["level"] == "info"
    assert parsed["timestamp"].endswith("Z")


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


def test_configure_logging_idempotent_across_calls(capfd):
    """Re-configuring should not duplicate output or break."""
    configure_logging(level="INFO", fmt="json")
    configure_logging(level="INFO", fmt="json")
    log = structlog.get_logger("aegis.test.idempotent")
    log.info("once_only")
    captured = capfd.readouterr()
    blob = captured.err + captured.out
    occurrences = sum(1 for line in blob.splitlines() if "once_only" in line)
    assert occurrences == 1, f"expected exactly one log line, got {occurrences}: {blob!r}"


def test_configure_logging_swaps_renderer_for_module_level_logger(capfd):
    """A module-level logger created before reconfiguration picks up the new renderer."""
    # Simulate the pattern from Task 7/9/14: module imports create the logger.
    module_log = structlog.get_logger("aegis.test.module_level")

    configure_logging(level="INFO", fmt="json")
    module_log.info("json_first")
    capfd.readouterr()  # discard

    configure_logging(level="INFO", fmt="console")
    module_log.info("console_second", marker="x")
    captured = capfd.readouterr()
    blob = captured.err + captured.out
    # console renderer output is not valid JSON; it includes the event name and key=value pairs.
    assert "console_second" in blob
    # The line containing console_second must NOT parse as JSON (would mean stale renderer).
    line = next(line for line in blob.splitlines() if "console_second" in line)
    try:
        json.loads(line)
        parsed_as_json = True
    except (json.JSONDecodeError, ValueError):
        parsed_as_json = False
    assert not parsed_as_json, f"line still rendering as JSON after reconfig: {line!r}"
