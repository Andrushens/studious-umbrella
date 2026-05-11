"""Shared pytest fixtures."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def db_url(tmp_path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path}/aegis-test.db"


@pytest_asyncio.fixture
async def engine(db_url: str) -> AsyncIterator[AsyncEngine]:
    from aegis.db import build_engine, init_db

    eng = build_engine(db_url)
    await init_db(eng)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    from aegis.db import build_sessionmaker

    sm = build_sessionmaker(engine)
    async with sm() as session:
        yield session
