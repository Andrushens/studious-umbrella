"""Shared pytest fixtures."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def db_url(tmp_path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path}/aegis-test.db"


@pytest.fixture
def settings(db_url: str):
    from aegis.config import Settings

    return Settings(
        database_url=db_url,
        etherscan_api_key="test-etherscan-key",
        etherscan_base_url="https://test-etherscan/api",
        alchemy_api_key="test-alchemy-key",
        alchemy_base_url_tmpl="https://test-alchemy/{api_key}",
        scheduler_enabled=False,
        log_format="console",
        sentry_dsn="",
        env="test",
        _env_file=None,
    )


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


@pytest_asyncio.fixture
async def app(settings):
    from aegis.main import create_app

    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
