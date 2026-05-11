"""Shared pytest fixtures (expanded in later tasks)."""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict | list:
    """Load a JSON fixture from tests/fixtures/."""
    return json.loads((FIXTURES_DIR / name).read_text())
