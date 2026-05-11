# Aegis Week 1 Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Aegis backend Week 1 deliverable: FastAPI service that registers iOS devices, accepts watched Ethereum wallet addresses, scans them for ERC-20 Approval events via Etherscan, caches token metadata via Alchemy, and persists current allowances in SQLite (WAL).

**Architecture:** Single FastAPI process. Async SQLAlchemy 2.x + aiosqlite + WAL pragma. httpx async clients for Etherscan + Alchemy with tenacity retry. APScheduler `AsyncIOScheduler` ticks every 60 min. structlog with stdlib bridge. Sentry opt-in via `SENTRY_DSN`. All test HTTP traffic mocked via `pytest-httpx`.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, SQLAlchemy 2.x async, aiosqlite, httpx[http2], pydantic-settings, APScheduler, structlog, sentry-sdk[fastapi], tenacity, eth-utils. Dev: pytest, pytest-asyncio, pytest-httpx, pytest-cov, ruff. Managed by `uv`.

**Working directory:** All commands assume `cd backend/` from repo root unless prefixed.

**Reference spec:** `docs/superpowers/specs/2026-05-11-aegis-week1-backend-design.md`.

---

## File map

| Path | Responsibility | Created in |
|---|---|---|
| `backend/pyproject.toml` | Project metadata + deps (uv) | Task 1 |
| `backend/uv.lock` | Lockfile | Task 1 |
| `backend/.env.example` | Env var template | Task 1 |
| `backend/.gitignore` | Ignore venv/db/caches | Task 1 |
| `backend/ruff.toml` | Lint config | Task 1 |
| `backend/README.md` | Run / test / env docs | Task 1 (skeleton), Task 16 (final) |
| `backend/src/aegis/__init__.py` | Package marker | Task 1 |
| `backend/src/aegis/eth.py` | APPROVAL_TOPIC, address helpers | Task 2 |
| `backend/src/aegis/config.py` | pydantic-settings Settings | Task 3 |
| `backend/src/aegis/logging.py` | structlog config | Task 4 |
| `backend/src/aegis/models.py` | SQLAlchemy ORM models | Task 5 |
| `backend/src/aegis/db.py` | Async engine, sessionmaker, WAL pragma, init_db | Task 5 |
| `backend/src/aegis/schemas.py` | Pydantic I/O + EthAddress type | Task 6 |
| `backend/src/aegis/clients/__init__.py` | Package marker | Task 7 |
| `backend/src/aegis/clients/base.py` | httpx factory + retry decorator | Task 7 |
| `backend/src/aegis/clients/etherscan.py` | Etherscan client | Task 7 |
| `backend/src/aegis/clients/alchemy.py` | Alchemy JSON-RPC client | Task 8 |
| `backend/src/aegis/errors.py` | Domain exceptions (`AegisError`, `NotFoundError`, `ConfigError`) | Task 10 |
| `backend/src/aegis/scanner.py` | scan_wallet + per-wallet lock | Task 9 |
| `backend/src/aegis/api/__init__.py` | Package marker | Task 10 |
| `backend/src/aegis/api/deps.py` | DI helpers | Task 10 |
| `backend/src/aegis/api/errors.py` | Exception → JSON handler registration | Task 10 |
| `backend/src/aegis/api/healthz.py` | `/v1/healthz` router | Task 10 |
| `backend/src/aegis/api/devices.py` | Devices/addresses/scan router | Tasks 11-13 |
| `backend/src/aegis/scheduler.py` | APScheduler + scan-all job | Task 14 |
| `backend/src/aegis/observability.py` | Sentry init | Task 15 |
| `backend/src/aegis/main.py` | App factory + lifespan + middleware | Task 10 (initial), Task 14 (scheduler wired), Task 15 (Sentry wired) |
| `backend/tests/__init__.py` | Package marker | Task 1 |
| `backend/tests/conftest.py` | Settings/engine/app/client fixtures | Tasks 1, 5, 10 (incremental) |
| `backend/tests/fixtures/etherscan_logs_simple.json` | 3-event sample | Task 7 |
| `backend/tests/fixtures/etherscan_logs_empty.json` | `{status:0, message:"No records found"}` | Task 7 |
| `backend/tests/fixtures/alchemy_token_metadata.json` | symbol/decimals RPC responses | Task 8 |
| `backend/tests/test_*.py` | Per-module tests | each task |

---

## Task 1: Project scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/ruff.toml`
- Create: `backend/README.md`
- Create: `backend/src/aegis/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create directory tree**

Run from repo root:
```bash
mkdir -p backend/src/aegis/api backend/src/aegis/clients backend/tests/fixtures
```

- [ ] **Step 2: Verify uv is installed**

Run:
```bash
uv --version
```
Expected: version printed (e.g., `uv 0.4.x`). If "command not found":
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL -l
uv --version
```

- [ ] **Step 3: Write `backend/pyproject.toml`**

```toml
[project]
name = "aegis-backend"
version = "0.1.0"
description = "Aegis crypto wallet security monitor — backend"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy[asyncio]>=2.0.25",
    "aiosqlite>=0.20",
    "httpx[http2]>=0.27",
    "pydantic-settings>=2.2",
    "apscheduler>=3.10",
    "structlog>=24.1",
    "sentry-sdk[fastapi]>=1.45",
    "tenacity>=8.2",
    "eth-utils>=4.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-httpx>=0.30",
    "pytest-cov>=4.1",
    "ruff>=0.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/aegis"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra --strict-markers"

[tool.coverage.run]
source = ["src/aegis"]
branch = true

[tool.coverage.report]
show_missing = true
skip_covered = false
```

- [ ] **Step 4: Write `backend/.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
*.db
*.db-wal
*.db-shm
.pytest_cache/
.ruff_cache/
htmlcov/
.coverage
dist/
build/
*.egg-info/
```

- [ ] **Step 5: Write `backend/.env.example`**

```
DATABASE_URL=sqlite+aiosqlite:///./aegis.db
ETHERSCAN_API_KEY=
ETHERSCAN_BASE_URL=https://api.etherscan.io/api
ALCHEMY_API_KEY=
ALCHEMY_BASE_URL_TMPL=https://eth-mainnet.g.alchemy.com/v2/{api_key}
LOG_LEVEL=INFO
LOG_FORMAT=console
SCHEDULER_ENABLED=true
SCAN_INTERVAL_MINUTES=60
SCAN_CONCURRENCY=4
HTTP_TIMEOUT_SECONDS=10
SENTRY_DSN=
ENV=development
```

- [ ] **Step 6: Write `backend/ruff.toml`**

```toml
line-length = 100
target-version = "py311"

[lint]
select = ["E", "F", "W", "I", "B", "UP", "N", "S"]
ignore = ["S101", "S105"]

[lint.per-file-ignores]
"tests/*" = ["S101", "S105", "S106", "S107"]
```

- [ ] **Step 7: Write `backend/README.md` (skeleton)**

```markdown
# Aegis Backend

FastAPI service that monitors EVM wallets for risky ERC-20 approvals.
Week 1 scope: Ethereum mainnet, Etherscan + Alchemy.

## Setup

```bash
cd backend
uv sync
cp .env.example .env
```

## Run

```bash
uv run uvicorn aegis.main:app --reload --port 8000
```

## Test

```bash
uv run pytest -q
uv run ruff check .
```
```

- [ ] **Step 8: Write `backend/src/aegis/__init__.py`**

```python
"""Aegis backend package."""

__version__ = "0.1.0"
```

- [ ] **Step 9: Write `backend/tests/__init__.py`**

(empty file)

```python
```

- [ ] **Step 10: Write minimal `backend/tests/conftest.py`**

```python
"""Shared pytest fixtures (expanded in later tasks)."""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict | list:
    """Load a JSON fixture from tests/fixtures/."""
    return json.loads((FIXTURES_DIR / name).read_text())
```

- [ ] **Step 11: Run `uv sync`**

Run from `backend/`:
```bash
cd backend && uv sync --all-extras
```
Expected: `Resolved N packages`, creates `.venv/` and `uv.lock`.

- [ ] **Step 12: Verify pytest collects zero tests successfully**

Run from `backend/`:
```bash
uv run pytest --collect-only -q
```
Expected: `no tests ran` or `0 tests collected` with exit code 5 (no tests yet). Either is fine — confirms pytest can import.

- [ ] **Step 13: Verify ruff runs**

Run:
```bash
uv run ruff check .
```
Expected: `All checks passed!` (no files to lint yet, or only the skeleton files pass).

- [ ] **Step 14: Commit**

From repo root:
```bash
git add backend
git commit -m "chore(backend): scaffold uv project + pytest/ruff config"
```

---

## Task 2: Ethereum helpers (`eth.py`)

**Files:**
- Create: `backend/src/aegis/eth.py`
- Create: `backend/tests/test_eth_helpers.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_eth_helpers.py`**

```python
"""Tests for aegis.eth helpers."""
from __future__ import annotations

import pytest

from aegis.eth import (
    APPROVAL_TOPIC,
    InvalidAddressError,
    normalize_address,
    pad_address_to_topic,
)


KNOWN_APPROVAL_TOPIC = (
    "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
)
VITALIK = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
VITALIK_LOWER = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


def test_approval_topic_matches_known_keccak():
    assert APPROVAL_TOPIC == KNOWN_APPROVAL_TOPIC


def test_normalize_address_lowercases_eip55_mixed_case():
    assert normalize_address(VITALIK) == VITALIK_LOWER


def test_normalize_address_passes_lowercase_unchanged():
    assert normalize_address(VITALIK_LOWER) == VITALIK_LOWER


def test_normalize_address_rejects_garbage():
    with pytest.raises(InvalidAddressError):
        normalize_address("hello world")


def test_normalize_address_rejects_short_hex():
    with pytest.raises(InvalidAddressError):
        normalize_address("0x1234")


def test_normalize_address_rejects_non_string():
    with pytest.raises(InvalidAddressError):
        normalize_address(123)  # type: ignore[arg-type]


def test_pad_address_to_topic_produces_32_bytes():
    topic = pad_address_to_topic(VITALIK)
    assert topic == "0x000000000000000000000000d8da6bf26964af9d7eed9e03e53415d37aa96045"
    assert len(topic) == 66  # "0x" + 64 hex chars
```

- [ ] **Step 2: Run tests to confirm they fail**

Run from `backend/`:
```bash
uv run pytest tests/test_eth_helpers.py -v
```
Expected: `ModuleNotFoundError: No module named 'aegis.eth'` (or collection error). All 7 tests fail.

- [ ] **Step 3: Implement `backend/src/aegis/eth.py`**

```python
"""Ethereum helpers: event topics, address validation/normalization."""
from __future__ import annotations

from eth_utils import is_address, keccak


class InvalidAddressError(ValueError):
    """Raised when an input string is not a valid Ethereum address."""


APPROVAL_TOPIC = "0x" + keccak(text="Approval(address,address,uint256)").hex()


def normalize_address(value: object) -> str:
    """Return lowercase 0x-prefixed address; raise InvalidAddressError on bad input."""
    if not isinstance(value, str) or not is_address(value):
        raise InvalidAddressError(f"Not a valid Ethereum address: {value!r}")
    return value.lower()


def pad_address_to_topic(address: str) -> str:
    """Return 0x-prefixed 32-byte hex topic from an address (for eth_getLogs topicN)."""
    normalized = normalize_address(address)
    hex_part = normalized[2:].rjust(64, "0")
    return "0x" + hex_part
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_eth_helpers.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/aegis/eth.py backend/tests/test_eth_helpers.py
git commit -m "feat(backend): add eth helpers (APPROVAL_TOPIC, address normalize/pad)"
```

---

## Task 3: Settings (`config.py`)

**Files:**
- Create: `backend/src/aegis/config.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_config.py`**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_config.py -v
```
Expected: collection error / `ModuleNotFoundError: No module named 'aegis.config'`.

- [ ] **Step 3: Implement `backend/src/aegis/config.py`**

```python
"""Application settings loaded from environment + optional .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./aegis.db"

    etherscan_api_key: str = ""
    etherscan_base_url: str = "https://api.etherscan.io/api"

    alchemy_api_key: str = ""
    alchemy_base_url_tmpl: str = "https://eth-mainnet.g.alchemy.com/v2/{api_key}"

    log_level: str = "INFO"
    log_format: str = "console"

    scheduler_enabled: bool = True
    scan_interval_minutes: int = 60
    scan_concurrency: int = 4

    http_timeout_seconds: float = 10.0

    sentry_dsn: str = ""
    env: str = "development"


def get_settings() -> Settings:
    """Build Settings; tests override via env or kwargs."""
    return Settings()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_config.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/aegis/config.py backend/tests/test_config.py
git commit -m "feat(backend): add pydantic-settings Settings"
```

---

## Task 4: Logging (`logging.py`)

**Files:**
- Create: `backend/src/aegis/logging.py`
- Create: `backend/tests/test_logging.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_logging.py`**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_logging.py -v
```
Expected: `ModuleNotFoundError: No module named 'aegis.logging'`.

- [ ] **Step 3: Implement `backend/src/aegis/logging.py`**

```python
"""structlog configuration with stdlib logging bridge."""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO", fmt: str = "console") -> None:
    """Configure structlog + stdlib logging.

    `fmt` is "console" (dev-friendly colored) or "json" (machine-readable).
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
    ]

    if fmt == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_logging.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/aegis/logging.py backend/tests/test_logging.py
git commit -m "feat(backend): add structlog config with stdlib bridge"
```

---

## Task 5: Models + DB engine (`models.py`, `db.py`)

**Files:**
- Create: `backend/src/aegis/models.py`
- Create: `backend/src/aegis/db.py`
- Create: `backend/tests/test_models.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add `db_url`, `engine`, `db_session` fixtures to `conftest.py`**

Replace `backend/tests/conftest.py` with:
```python
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
```

- [ ] **Step 2: Write failing tests `backend/tests/test_models.py`**

```python
"""Tests for ORM models + DB engine."""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.models import Approval, Device, Token, WatchedAddress


async def test_create_device(db_session: AsyncSession):
    d = Device(id="dev-1", push_token="tok", tier="free")
    db_session.add(d)
    await db_session.commit()
    loaded = await db_session.get(Device, "dev-1")
    assert loaded is not None
    assert loaded.tier == "free"
    assert loaded.created_at is not None
    assert loaded.updated_at is not None


async def test_watched_address_unique(db_session: AsyncSession):
    db_session.add(Device(id="dev-2", tier="free"))
    await db_session.flush()
    db_session.add(
        WatchedAddress(device_id="dev-2", address="0xaaa", chain="ethereum")
    )
    await db_session.flush()
    db_session.add(
        WatchedAddress(device_id="dev-2", address="0xaaa", chain="ethereum")
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_token_unique_chain_address(db_session: AsyncSession):
    db_session.add(Token(chain="ethereum", address="0xtok", symbol="X"))
    await db_session.flush()
    db_session.add(Token(chain="ethereum", address="0xtok"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_approval_unique_constraint(db_session: AsyncSession):
    db_session.add(Device(id="dev-3"))
    await db_session.flush()
    addr = WatchedAddress(device_id="dev-3", address="0xa", chain="ethereum")
    tok = Token(chain="ethereum", address="0xtok2")
    db_session.add_all([addr, tok])
    await db_session.flush()
    db_session.add(
        Approval(
            watched_address_id=addr.id,
            token_id=tok.id,
            spender="0xspender",
            amount="0",
            block_number=1,
            tx_hash="0xtx",
        )
    )
    await db_session.flush()
    db_session.add(
        Approval(
            watched_address_id=addr.id,
            token_id=tok.id,
            spender="0xspender",
            amount="100",
            block_number=2,
            tx_hash="0xtx2",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_cascade_delete_device_removes_addresses(db_session: AsyncSession):
    db_session.add(Device(id="dev-4"))
    db_session.add(WatchedAddress(device_id="dev-4", address="0xb", chain="ethereum"))
    await db_session.commit()
    dev = await db_session.get(Device, "dev-4")
    await db_session.delete(dev)
    await db_session.commit()
    rows = (
        await db_session.execute(
            select(WatchedAddress).where(WatchedAddress.device_id == "dev-4")
        )
    ).scalars().all()
    assert rows == []


async def test_wal_pragma_is_enabled(engine):
    async with engine.connect() as conn:
        result = await conn.exec_driver_sql("PRAGMA journal_mode;")
        mode = result.scalar()
    assert mode.lower() == "wal"
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
uv run pytest tests/test_models.py -v
```
Expected: collection error / `ModuleNotFoundError: No module named 'aegis.models'`.

- [ ] **Step 4: Implement `backend/src/aegis/models.py`**

```python
"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "device"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    push_token: Mapped[str | None] = mapped_column(String, nullable=True)
    tier: Mapped[str] = mapped_column(String, default="free", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    addresses: Mapped[list["WatchedAddress"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class WatchedAddress(Base):
    __tablename__ = "watched_address"
    __table_args__ = (
        UniqueConstraint("device_id", "address", "chain", name="uq_watched_addr"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    address: Mapped[str] = mapped_column(String, nullable=False)
    chain: Mapped[str] = mapped_column(String, default="ethereum", nullable=False)
    nickname: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    device: Mapped["Device"] = relationship(back_populates="addresses")
    approvals: Mapped[list["Approval"]] = relationship(
        back_populates="watched_address", cascade="all, delete-orphan"
    )


class Token(Base):
    __tablename__ = "token"
    __table_args__ = (UniqueConstraint("chain", "address", name="uq_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    decimals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class Approval(Base):
    __tablename__ = "approval"
    __table_args__ = (
        UniqueConstraint(
            "watched_address_id", "token_id", "spender", name="uq_approval"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watched_address_id: Mapped[int] = mapped_column(
        ForeignKey("watched_address.id", ondelete="CASCADE"), nullable=False
    )
    token_id: Mapped[int] = mapped_column(ForeignKey("token.id"), nullable=False)
    spender: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[str] = mapped_column(String, nullable=False)
    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tx_hash: Mapped[str] = mapped_column(String, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    watched_address: Mapped["WatchedAddress"] = relationship(back_populates="approvals")
    token: Mapped["Token"] = relationship()
```

- [ ] **Step 5: Implement `backend/src/aegis/db.py`**

```python
"""Async SQLAlchemy engine + session factory + SQLite WAL setup."""
from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from aegis.models import Base


def build_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(database_url, future=True)
    _enable_sqlite_pragmas(engine)
    return engine


def _enable_sqlite_pragmas(engine: AsyncEngine) -> None:
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
uv run pytest tests/test_models.py -v
```
Expected: 6 passed.

- [ ] **Step 7: Run full suite + ruff**

```bash
uv run pytest -q
uv run ruff check .
```
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add backend/src/aegis/models.py backend/src/aegis/db.py \
        backend/tests/test_models.py backend/tests/conftest.py
git commit -m "feat(backend): add ORM models + async SQLAlchemy engine with WAL"
```

---

## Task 6: Pydantic schemas (`schemas.py`)

**Files:**
- Create: `backend/src/aegis/schemas.py`
- Create: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_schemas.py`**

```python
"""Tests for Pydantic I/O schemas + EthAddress type."""
from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from aegis.schemas import (
    AddressCreate,
    DeviceCreate,
    EthAddress,
)


VITALIK_MIXED = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
VITALIK_LOWER = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


class _Wrap(BaseModel):
    addr: EthAddress


def test_eth_address_normalizes_to_lowercase():
    w = _Wrap(addr=VITALIK_MIXED)
    assert w.addr == VITALIK_LOWER


def test_eth_address_rejects_garbage():
    with pytest.raises(ValidationError):
        _Wrap(addr="not an address")


def test_eth_address_rejects_short_hex():
    with pytest.raises(ValidationError):
        _Wrap(addr="0x1234")


def test_device_create_defaults():
    d = DeviceCreate(device_id="abc")
    assert d.device_id == "abc"
    assert d.push_token is None
    assert d.tier == "free"


def test_device_create_tier_validation():
    with pytest.raises(ValidationError):
        DeviceCreate(device_id="abc", tier="enterprise")


def test_address_create_defaults_chain():
    a = AddressCreate(address=VITALIK_MIXED)
    assert a.address == VITALIK_LOWER
    assert a.chain == "ethereum"
    assert a.nickname is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_schemas.py -v
```
Expected: collection error / `ModuleNotFoundError: No module named 'aegis.schemas'`.

- [ ] **Step 3: Implement `backend/src/aegis/schemas.py`**

```python
"""Pydantic I/O schemas + EthAddress type."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict

from aegis.eth import InvalidAddressError, normalize_address


def _validate_eth_address(v: object) -> str:
    if not isinstance(v, str):
        raise ValueError("address must be a string")
    try:
        return normalize_address(v)
    except InvalidAddressError as e:
        raise ValueError(str(e)) from e


EthAddress = Annotated[str, BeforeValidator(_validate_eth_address)]


class DeviceCreate(BaseModel):
    device_id: str
    push_token: str | None = None
    tier: Literal["free", "pro"] = "free"


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    push_token: str | None
    tier: str
    created_at: datetime
    updated_at: datetime


class AddressCreate(BaseModel):
    address: EthAddress
    chain: str = "ethereum"
    nickname: str | None = None


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    address: str
    chain: str
    nickname: str | None
    created_at: datetime


class AddressList(BaseModel):
    addresses: list[AddressOut]


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chain: str
    address: str
    symbol: str | None
    decimals: int | None
    name: str | None


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: TokenOut
    spender: str
    amount: str
    block_number: int
    tx_hash: str
    first_seen_at: datetime
    last_seen_at: datetime


class ApprovalList(BaseModel):
    approvals: list[ApprovalOut]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_schemas.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/aegis/schemas.py backend/tests/test_schemas.py
git commit -m "feat(backend): add Pydantic schemas + EthAddress type"
```

---

## Task 7: Etherscan client + HTTP base (`clients/base.py`, `clients/etherscan.py`)

**Files:**
- Create: `backend/src/aegis/clients/__init__.py`
- Create: `backend/src/aegis/clients/base.py`
- Create: `backend/src/aegis/clients/etherscan.py`
- Create: `backend/tests/fixtures/etherscan_logs_simple.json`
- Create: `backend/tests/fixtures/etherscan_logs_empty.json`
- Create: `backend/tests/test_clients_etherscan.py`

- [ ] **Step 1: Create `backend/src/aegis/clients/__init__.py`** (empty)

```python
```

- [ ] **Step 2: Write fixture `backend/tests/fixtures/etherscan_logs_simple.json`**

This fixture has 3 logs covering 2 distinct (token, spender) pairs, with pair A having two events — the later one supersedes. Addresses are real-shaped but invented.

```json
{
  "status": "1",
  "message": "OK",
  "result": [
    {
      "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "topics": [
        "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",
        "0x000000000000000000000000d8da6bf26964af9d7eed9e03e53415d37aa96045",
        "0x0000000000000000000000001111111254eeb25477b68fb85ed929f73a960582"
      ],
      "data": "0x00000000000000000000000000000000000000000000000000000000ffffffff",
      "blockNumber": "0x100",
      "transactionHash": "0xaaaa1",
      "logIndex": "0x0"
    },
    {
      "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
      "topics": [
        "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",
        "0x000000000000000000000000d8da6bf26964af9d7eed9e03e53415d37aa96045",
        "0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88"
      ],
      "data": "0x000000000000000000000000000000000000000000000000016345785d8a0000",
      "blockNumber": "0x101",
      "transactionHash": "0xbbbb1",
      "logIndex": "0x1"
    },
    {
      "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "topics": [
        "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",
        "0x000000000000000000000000d8da6bf26964af9d7eed9e03e53415d37aa96045",
        "0x0000000000000000000000001111111254eeb25477b68fb85ed929f73a960582"
      ],
      "data": "0x0000000000000000000000000000000000000000000000000000000000000000",
      "blockNumber": "0x102",
      "transactionHash": "0xaaaa2",
      "logIndex": "0x0"
    }
  ]
}
```

- [ ] **Step 3: Write fixture `backend/tests/fixtures/etherscan_logs_empty.json`**

```json
{
  "status": "0",
  "message": "No records found",
  "result": []
}
```

- [ ] **Step 4: Write failing tests `backend/tests/test_clients_etherscan.py`**

```python
"""Tests for Etherscan client (Approval-event getLogs)."""
from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from aegis.clients.etherscan import (
    ApprovalEvent,
    EtherscanClient,
    EtherscanError,
    RateLimitedError,
)
from tests.conftest import load_fixture

BASE_URL = "https://test-etherscan/api"
OWNER = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"


async def _client() -> EtherscanClient:
    return EtherscanClient(
        httpx.AsyncClient(timeout=5.0),
        api_key="test-key",
        base_url=BASE_URL,
    )


async def test_get_approval_logs_parses_three_events(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url__startswith=BASE_URL, json=load_fixture("etherscan_logs_simple.json"))
    es = await _client()
    events = await es.get_approval_logs(OWNER)
    assert len(events) == 3
    assert events[0].token == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert events[0].spender == "0x1111111254eeb25477b68fb85ed929f73a960582"
    assert events[0].amount == "4294967295"  # 0xffffffff
    assert events[0].block_number == 0x100
    assert events[0].tx_hash == "0xaaaa1"
    assert events[2].amount == "0"  # revoke event


async def test_get_approval_logs_builds_correct_params(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url__startswith=BASE_URL, json={"status": "1", "message": "OK", "result": []})
    es = await _client()
    await es.get_approval_logs(OWNER, from_block=100, to_block=200)
    request = httpx_mock.get_request()
    assert request is not None
    qp = dict(request.url.params)
    assert qp["module"] == "logs"
    assert qp["action"] == "getLogs"
    assert qp["topic0"] == "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
    assert qp["topic1"] == "0x000000000000000000000000d8da6bf26964af9d7eed9e03e53415d37aa96045"
    assert qp["fromBlock"] == "100"
    assert qp["toBlock"] == "200"
    assert qp["apikey"] == "test-key"
    assert qp["offset"] == "1000"
    assert qp["page"] == "1"


async def test_get_approval_logs_empty_returns_empty_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url__startswith=BASE_URL, json=load_fixture("etherscan_logs_empty.json"))
    es = await _client()
    assert await es.get_approval_logs(OWNER) == []


async def test_get_approval_logs_paginates(httpx_mock: HTTPXMock):
    page1_logs = load_fixture("etherscan_logs_simple.json")["result"]
    # Build a fake 1000-log page (duplicate the first log 1000 times).
    big_page = {"status": "1", "message": "OK", "result": [page1_logs[0]] * 1000}
    httpx_mock.add_response(url__startswith=BASE_URL, json=big_page)
    httpx_mock.add_response(url__startswith=BASE_URL, json={"status": "1", "message": "OK", "result": [page1_logs[1]]})
    es = await _client()
    events = await es.get_approval_logs(OWNER)
    assert len(events) == 1001
    # Verify two HTTP calls made
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert dict(requests[0].url.params)["page"] == "1"
    assert dict(requests[1].url.params)["page"] == "2"


async def test_get_approval_logs_rate_limited(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__startswith=BASE_URL,
        json={"status": "0", "message": "Max rate limit reached", "result": "Max rate limit reached"},
    )
    es = await _client()
    with pytest.raises(RateLimitedError):
        await es.get_approval_logs(OWNER)


async def test_get_approval_logs_other_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__startswith=BASE_URL,
        json={"status": "0", "message": "NOTOK", "result": "Invalid API Key"},
    )
    es = await _client()
    with pytest.raises(EtherscanError):
        await es.get_approval_logs(OWNER)


def test_approval_event_is_frozen_dataclass():
    ev = ApprovalEvent(
        token="0xa", spender="0xb", amount="0", block_number=1, tx_hash="0xtx", log_index=0
    )
    with pytest.raises(Exception):
        ev.amount = "100"  # type: ignore[misc]
```

- [ ] **Step 5: Run tests to confirm they fail**

```bash
uv run pytest tests/test_clients_etherscan.py -v
```
Expected: collection error / `ModuleNotFoundError`.

- [ ] **Step 6: Implement `backend/src/aegis/clients/base.py`**

```python
"""Shared HTTP client utilities — factory + tenacity retry."""
from __future__ import annotations

import httpx
import tenacity


def build_http_client(timeout: float = 10.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout, http2=True)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


http_retry = tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=0.5, max=4),
    retry=tenacity.retry_if_exception(_is_retryable),
    reraise=True,
)
```

- [ ] **Step 7: Implement `backend/src/aegis/clients/etherscan.py`**

```python
"""Etherscan API client — getLogs for ERC-20 Approval events."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from aegis.clients.base import http_retry
from aegis.eth import APPROVAL_TOPIC, normalize_address, pad_address_to_topic


class EtherscanError(RuntimeError):
    """Etherscan responded with a non-success status."""


class RateLimitedError(EtherscanError):
    """Etherscan rate limit was hit."""


@dataclass(frozen=True, slots=True)
class ApprovalEvent:
    token: str
    spender: str
    amount: str
    block_number: int
    tx_hash: str
    log_index: int


class EtherscanClient:
    PAGE_SIZE = 1000

    def __init__(self, http: httpx.AsyncClient, api_key: str, base_url: str) -> None:
        self._http = http
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def get_approval_logs(
        self,
        owner: str,
        from_block: int = 0,
        to_block: int | str = "latest",
    ) -> list[ApprovalEvent]:
        owner_topic = pad_address_to_topic(owner)
        events: list[ApprovalEvent] = []
        page = 1
        while True:
            params = {
                "module": "logs",
                "action": "getLogs",
                "fromBlock": from_block,
                "toBlock": to_block,
                "topic0": APPROVAL_TOPIC,
                "topic1": owner_topic,
                "page": page,
                "offset": self.PAGE_SIZE,
                "apikey": self._api_key,
            }
            body = await self._fetch(params)
            status = str(body.get("status", "1"))
            message = body.get("message", "")
            result = body.get("result")

            if status == "0":
                if message == "No records found":
                    return events
                if isinstance(message, str) and "rate limit" in message.lower():
                    raise RateLimitedError(message)
                raise EtherscanError(f"Etherscan error: {message} ({result})")

            if not isinstance(result, list):
                raise EtherscanError(f"Unexpected Etherscan result: {result!r}")

            for log in result:
                events.append(self._parse_log(log))

            if len(result) < self.PAGE_SIZE:
                return events
            page += 1

    @http_retry
    async def _fetch(self, params: dict) -> dict:
        resp = await self._http.get(self._base_url, params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse_log(log: dict) -> ApprovalEvent:
        topics = log["topics"]
        spender_topic = topics[2]
        spender = "0x" + spender_topic[-40:]
        data = log["data"]
        amount_int = int(data, 16) if data and data != "0x" else 0
        return ApprovalEvent(
            token=normalize_address(log["address"]),
            spender=normalize_address(spender),
            amount=str(amount_int),
            block_number=int(log["blockNumber"], 16),
            tx_hash=log["transactionHash"],
            log_index=int(log["logIndex"], 16),
        )
```

- [ ] **Step 8: Run tests to confirm they pass**

```bash
uv run pytest tests/test_clients_etherscan.py -v
```
Expected: 7 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/src/aegis/clients/ backend/tests/fixtures/etherscan_logs_simple.json \
        backend/tests/fixtures/etherscan_logs_empty.json \
        backend/tests/test_clients_etherscan.py
git commit -m "feat(backend): add Etherscan client (Approval getLogs + retry)"
```

---

## Task 8: Alchemy client (`clients/alchemy.py`)

**Files:**
- Create: `backend/src/aegis/clients/alchemy.py`
- Create: `backend/tests/fixtures/alchemy_token_metadata.json`
- Create: `backend/tests/test_clients_alchemy.py`

- [ ] **Step 1: Write fixture `backend/tests/fixtures/alchemy_token_metadata.json`**

USDC: symbol="USDC", decimals=6. ABI-encoded responses below.

```json
{
  "symbol_usdc": {
    "jsonrpc": "2.0",
    "id": 1,
    "result": "0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000455534443000000000000000000000000000000000000000000000000000000"
  },
  "decimals_usdc": {
    "jsonrpc": "2.0",
    "id": 1,
    "result": "0x0000000000000000000000000000000000000000000000000000000000000006"
  },
  "block_number": {
    "jsonrpc": "2.0",
    "id": 1,
    "result": "0x10c8a47"
  },
  "rpc_error": {
    "jsonrpc": "2.0",
    "id": 1,
    "error": {"code": -32000, "message": "execution reverted"}
  }
}
```

Note: ensure the symbol hex above decodes to "USDC". The structure is:
- 32 bytes offset (`0x...20`)
- 32 bytes length (`0x...04`)
- right-padded UTF-8 bytes `55534443` = "USDC"

- [ ] **Step 2: Write failing tests `backend/tests/test_clients_alchemy.py`**

```python
"""Tests for Alchemy JSON-RPC client."""
from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from aegis.clients.alchemy import (
    AlchemyClient,
    AlchemyError,
    TokenMetadata,
)
from tests.conftest import load_fixture

BASE_TMPL = "https://test-alchemy/{api_key}"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def _client() -> AlchemyClient:
    return AlchemyClient(
        httpx.AsyncClient(timeout=5.0),
        api_key="test-alchemy-key",
        base_url_tmpl=BASE_TMPL,
    )


async def test_eth_block_number(httpx_mock: HTTPXMock):
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(url="https://test-alchemy/test-alchemy-key", json=fixtures["block_number"])
    c = _client()
    bn = await c.eth_block_number()
    assert bn == 0x10C8A47


async def test_eth_call_payload_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test-alchemy/test-alchemy-key",
        json={"jsonrpc": "2.0", "id": 1, "result": "0xdeadbeef"},
    )
    c = _client()
    result = await c.eth_call(USDC, "0x95d89b41")
    assert result == "0xdeadbeef"
    req = httpx_mock.get_request()
    body = req.read()
    import json as _json
    payload = _json.loads(body)
    assert payload["jsonrpc"] == "2.0"
    assert payload["method"] == "eth_call"
    assert payload["params"][0] == {"to": USDC, "data": "0x95d89b41"}
    assert payload["params"][1] == "latest"


async def test_eth_call_raises_on_rpc_error(httpx_mock: HTTPXMock):
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(url="https://test-alchemy/test-alchemy-key", json=fixtures["rpc_error"])
    c = _client()
    with pytest.raises(AlchemyError):
        await c.eth_call(USDC, "0x95d89b41")


async def test_get_erc20_metadata_decodes_string_and_uint8(httpx_mock: HTTPXMock):
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(url="https://test-alchemy/test-alchemy-key", json=fixtures["symbol_usdc"])
    httpx_mock.add_response(url="https://test-alchemy/test-alchemy-key", json=fixtures["decimals_usdc"])
    c = _client()
    meta = await c.get_erc20_metadata(USDC)
    assert meta == TokenMetadata(symbol="USDC", decimals=6, name=None)


async def test_get_erc20_metadata_falls_back_on_revert(httpx_mock: HTTPXMock):
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(url="https://test-alchemy/test-alchemy-key", json=fixtures["rpc_error"])
    httpx_mock.add_response(url="https://test-alchemy/test-alchemy-key", json=fixtures["rpc_error"])
    c = _client()
    meta = await c.get_erc20_metadata(USDC)
    assert meta.symbol is None
    assert meta.decimals is None
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
uv run pytest tests/test_clients_alchemy.py -v
```
Expected: collection error / `ModuleNotFoundError: No module named 'aegis.clients.alchemy'`.

- [ ] **Step 4: Implement `backend/src/aegis/clients/alchemy.py`**

```python
"""Alchemy JSON-RPC client + ERC-20 metadata helper."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from aegis.clients.base import http_retry


class AlchemyError(RuntimeError):
    """Alchemy responded with an error object or unexpected payload."""


@dataclass(frozen=True, slots=True)
class TokenMetadata:
    symbol: str | None
    decimals: int | None
    name: str | None = None


SYMBOL_SELECTOR = "0x95d89b41"
DECIMALS_SELECTOR = "0x313ce567"


class AlchemyClient:
    def __init__(
        self, http: httpx.AsyncClient, api_key: str, base_url_tmpl: str
    ) -> None:
        self._http = http
        self._url = base_url_tmpl.format(api_key=api_key)

    @http_retry
    async def _post(self, payload: dict) -> dict:
        resp = await self._http.post(self._url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def _rpc(self, method: str, params: list) -> object:
        body = await self._post(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        )
        if "error" in body:
            raise AlchemyError(body["error"].get("message", "Alchemy RPC error"))
        return body["result"]

    async def eth_block_number(self) -> int:
        result = await self._rpc("eth_blockNumber", [])
        assert isinstance(result, str)
        return int(result, 16)

    async def eth_call(self, to: str, data: str, block: str = "latest") -> str:
        result = await self._rpc("eth_call", [{"to": to, "data": data}, block])
        assert isinstance(result, str)
        return result

    async def get_erc20_metadata(self, token_address: str) -> TokenMetadata:
        symbol = await self._try_call(token_address, SYMBOL_SELECTOR, _decode_string)
        decimals = await self._try_call(
            token_address, DECIMALS_SELECTOR, _decode_uint8
        )
        return TokenMetadata(symbol=symbol, decimals=decimals)

    async def _try_call(self, to: str, data: str, decoder):
        try:
            raw = await self.eth_call(to, data)
        except AlchemyError:
            return None
        if not raw or raw == "0x":
            return None
        try:
            return decoder(raw)
        except (ValueError, IndexError, UnicodeDecodeError):
            return None


def _decode_string(hex_data: str) -> str:
    """Decode a Solidity-encoded `string` return value.

    Handles both ABI-encoded dynamic strings (offset+length+bytes) and the
    legacy `bytes32` form used by tokens like MKR.
    """
    raw = bytes.fromhex(hex_data[2:])
    if len(raw) == 32:
        return raw.rstrip(b"\x00").decode("utf-8", errors="replace")
    length = int.from_bytes(raw[32:64], "big")
    return raw[64 : 64 + length].decode("utf-8", errors="replace")


def _decode_uint8(hex_data: str) -> int:
    return int(hex_data, 16) & 0xFF
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run pytest tests/test_clients_alchemy.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -q
uv run ruff check .
```
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/src/aegis/clients/alchemy.py \
        backend/tests/fixtures/alchemy_token_metadata.json \
        backend/tests/test_clients_alchemy.py
git commit -m "feat(backend): add Alchemy client + ERC-20 metadata decoder"
```

---

## Task 9: Scanner (`scanner.py`)

**Files:**
- Create: `backend/src/aegis/scanner.py`
- Create: `backend/tests/test_scanner.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_scanner.py`**

```python
"""Tests for scanner.scan_wallet."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.clients.alchemy import TokenMetadata
from aegis.clients.etherscan import ApprovalEvent
from aegis.models import Approval, Device, Token, WatchedAddress
from aegis.scanner import scan_wallet


USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT = "0xdac17f958d2ee523a2206206994597c13d831ec7"
SPENDER_A = "0x1111111254eeb25477b68fb85ed929f73a960582"
SPENDER_B = "0xc36442b4a4522e871399cd717abdd847ab11fe88"


async def _seed_watched(session: AsyncSession) -> WatchedAddress:
    session.add(Device(id="dev-scan"))
    addr = WatchedAddress(
        device_id="dev-scan",
        address="0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
        chain="ethereum",
    )
    session.add(addr)
    await session.commit()
    await session.refresh(addr)
    return addr


def _events_for_scan() -> list[ApprovalEvent]:
    return [
        ApprovalEvent(token=USDC, spender=SPENDER_A, amount="4294967295", block_number=0x100, tx_hash="0xaaaa1", log_index=0),
        ApprovalEvent(token=USDT, spender=SPENDER_B, amount="100000000", block_number=0x101, tx_hash="0xbbbb1", log_index=1),
        ApprovalEvent(token=USDC, spender=SPENDER_A, amount="0", block_number=0x102, tx_hash="0xaaaa2", log_index=0),
    ]


async def test_scan_wallet_persists_two_approvals(db_session: AsyncSession):
    watched = await _seed_watched(db_session)
    etherscan = AsyncMock()
    etherscan.get_approval_logs.return_value = _events_for_scan()
    alchemy = AsyncMock()
    alchemy.get_erc20_metadata.side_effect = [
        TokenMetadata(symbol="USDC", decimals=6),
        TokenMetadata(symbol="USDT", decimals=6),
    ]

    approvals = await scan_wallet(db_session, watched, etherscan, alchemy)
    assert len(approvals) == 2

    rows = (await db_session.execute(select(Approval))).scalars().all()
    by_spender = {r.spender: r for r in rows}
    assert by_spender[SPENDER_A].amount == "0"  # latest event was revoke
    assert by_spender[SPENDER_A].block_number == 0x102
    assert by_spender[SPENDER_B].amount == "100000000"

    tokens = (await db_session.execute(select(Token))).scalars().all()
    assert {t.address for t in tokens} == {USDC, USDT}
    assert {t.symbol for t in tokens} == {"USDC", "USDT"}


async def test_scan_wallet_rescan_updates_last_seen_not_first_seen(db_session: AsyncSession):
    watched = await _seed_watched(db_session)
    etherscan = AsyncMock()
    etherscan.get_approval_logs.return_value = _events_for_scan()
    alchemy = AsyncMock()
    alchemy.get_erc20_metadata.side_effect = [
        TokenMetadata(symbol="USDC", decimals=6),
        TokenMetadata(symbol="USDT", decimals=6),
    ]

    first_run = await scan_wallet(db_session, watched, etherscan, alchemy)
    first_seen_map = {a.spender: a.first_seen_at for a in first_run}

    etherscan.get_approval_logs.return_value = _events_for_scan()
    # Second scan: only return previously seen tokens; metadata not refetched
    alchemy.get_erc20_metadata.side_effect = AssertionError("should not be called")

    second_run = await scan_wallet(db_session, watched, etherscan, alchemy)
    for ap in second_run:
        assert ap.first_seen_at == first_seen_map[ap.spender]
        assert ap.last_seen_at >= first_seen_map[ap.spender]


async def test_scan_wallet_serializes_overlapping_for_same_wallet(db_session: AsyncSession):
    watched = await _seed_watched(db_session)
    etherscan = AsyncMock()
    events = _events_for_scan()
    started = asyncio.Event()
    finish = asyncio.Event()

    async def slow_logs(_):
        started.set()
        await finish.wait()
        return events

    etherscan.get_approval_logs.side_effect = slow_logs
    alchemy = AsyncMock()
    alchemy.get_erc20_metadata.side_effect = [
        TokenMetadata(symbol="USDC", decimals=6),
        TokenMetadata(symbol="USDT", decimals=6),
    ]

    task1 = asyncio.create_task(scan_wallet(db_session, watched, etherscan, alchemy))
    await started.wait()
    # Second scan must NOT start until first finishes
    task2 = asyncio.create_task(scan_wallet(db_session, watched, etherscan, alchemy))
    await asyncio.sleep(0.05)
    assert etherscan.get_approval_logs.call_count == 1  # second is blocked on lock

    finish.set()
    await asyncio.gather(task1, task2)
    assert etherscan.get_approval_logs.call_count == 2
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_scanner.py -v
```
Expected: collection error / `ModuleNotFoundError: No module named 'aegis.scanner'`.

- [ ] **Step 3: Implement `backend/src/aegis/scanner.py`**

```python
"""Wallet scanner — pulls Approval logs, upserts current allowances + token metadata."""
from __future__ import annotations

import asyncio
import weakref
from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.clients.alchemy import AlchemyClient
from aegis.clients.etherscan import ApprovalEvent, EtherscanClient
from aegis.models import Approval, Token, WatchedAddress

_locks: weakref.WeakValueDictionary[tuple[str, str, str], asyncio.Lock] = (
    weakref.WeakValueDictionary()
)


def _lock_for(device_id: str, address: str, chain: str) -> asyncio.Lock:
    key = (device_id, address, chain)
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


async def scan_wallet(
    session: AsyncSession,
    watched: WatchedAddress,
    etherscan: EtherscanClient,
    alchemy: AlchemyClient,
) -> list[Approval]:
    """Scan a single watched address. Returns the current Approval rows for it."""
    async with _lock_for(watched.device_id, watched.address, watched.chain):
        events = await etherscan.get_approval_logs(watched.address)
        latest_by_pair = _reduce_latest(events)
        token_addrs = {ev.token for ev in latest_by_pair.values()}
        tokens_by_addr = await _ensure_tokens(
            session, watched.chain, token_addrs, alchemy
        )
        approvals = await _upsert_approvals(
            session, watched, latest_by_pair, tokens_by_addr
        )
        await session.commit()
        return approvals


def _reduce_latest(
    events: Iterable[ApprovalEvent],
) -> dict[tuple[str, str], ApprovalEvent]:
    latest: dict[tuple[str, str], ApprovalEvent] = {}
    for ev in events:
        latest[(ev.token, ev.spender)] = ev
    return latest


async def _ensure_tokens(
    session: AsyncSession,
    chain: str,
    addresses: set[str],
    alchemy: AlchemyClient,
) -> dict[str, Token]:
    if not addresses:
        return {}
    existing = (
        await session.execute(
            select(Token).where(Token.chain == chain, Token.address.in_(addresses))
        )
    ).scalars().all()
    by_addr: dict[str, Token] = {t.address: t for t in existing}
    for addr in addresses - by_addr.keys():
        meta = await alchemy.get_erc20_metadata(addr)
        token = Token(
            chain=chain,
            address=addr,
            symbol=meta.symbol,
            decimals=meta.decimals,
            name=meta.name,
        )
        session.add(token)
        by_addr[addr] = token
    await session.flush()
    return by_addr


async def _upsert_approvals(
    session: AsyncSession,
    watched: WatchedAddress,
    latest_by_pair: dict[tuple[str, str], ApprovalEvent],
    tokens_by_addr: dict[str, Token],
) -> list[Approval]:
    now = datetime.now(timezone.utc)
    existing = (
        await session.execute(
            select(Approval).where(Approval.watched_address_id == watched.id)
        )
    ).scalars().all()
    by_key: dict[tuple[int, str], Approval] = {
        (a.token_id, a.spender): a for a in existing
    }

    result: list[Approval] = []
    for (token_addr, spender), ev in latest_by_pair.items():
        token = tokens_by_addr[token_addr]
        key = (token.id, spender)
        row = by_key.get(key)
        if row is None:
            row = Approval(
                watched_address_id=watched.id,
                token_id=token.id,
                spender=spender,
                amount=ev.amount,
                block_number=ev.block_number,
                tx_hash=ev.tx_hash,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(row)
        else:
            row.amount = ev.amount
            row.block_number = ev.block_number
            row.tx_hash = ev.tx_hash
            row.last_seen_at = now
        result.append(row)
    return result
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_scanner.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/aegis/scanner.py backend/tests/test_scanner.py
git commit -m "feat(backend): add scan_wallet with per-wallet asyncio lock"
```

---

## Task 10: FastAPI app skeleton + healthz + error handlers + `main.py`

**Files:**
- Create: `backend/src/aegis/errors.py`
- Create: `backend/src/aegis/api/__init__.py`
- Create: `backend/src/aegis/api/deps.py`
- Create: `backend/src/aegis/api/errors.py`
- Create: `backend/src/aegis/api/healthz.py`
- Create: `backend/src/aegis/main.py`
- Modify: `backend/tests/conftest.py` (add `app`, `client` fixtures)
- Create: `backend/tests/test_healthz.py`
- Create: `backend/tests/test_errors.py`

- [ ] **Step 1: Implement `backend/src/aegis/errors.py`**

```python
"""Domain exceptions."""
from __future__ import annotations


class AegisError(Exception):
    code: str = "internal_error"
    status_code: int = 500


class NotFoundError(AegisError):
    code = "not_found"
    status_code = 404


class ConfigError(AegisError):
    code = "not_configured"
    status_code = 503
```

- [ ] **Step 2: Create `backend/src/aegis/api/__init__.py`** (empty)

```python
```

- [ ] **Step 3: Implement `backend/src/aegis/api/deps.py`**

```python
"""FastAPI dependency providers."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.clients.alchemy import AlchemyClient
from aegis.clients.etherscan import EtherscanClient
from aegis.config import Settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_etherscan(request: Request) -> EtherscanClient:
    return request.app.state.etherscan


def get_alchemy(request: Request) -> AlchemyClient:
    return request.app.state.alchemy


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
EtherscanDep = Annotated[EtherscanClient, Depends(get_etherscan)]
AlchemyDep = Annotated[AlchemyClient, Depends(get_alchemy)]
```

- [ ] **Step 4: Implement `backend/src/aegis/api/errors.py`**

```python
"""Exception → JSON handler registration."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aegis.clients.alchemy import AlchemyError
from aegis.clients.etherscan import EtherscanError, RateLimitedError
from aegis.errors import AegisError, ConfigError, NotFoundError
from aegis.eth import InvalidAddressError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidAddressError)
    async def _invalid_address(_: Request, exc: InvalidAddressError):
        return _err(422, "invalid_address", str(exc))

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError):
        return _err(404, "not_found", str(exc))

    @app.exception_handler(ConfigError)
    async def _not_configured(_: Request, exc: ConfigError):
        return _err(503, "not_configured", str(exc))

    @app.exception_handler(RateLimitedError)
    async def _rate_limited(_: Request, exc: RateLimitedError):
        return _err(503, "upstream_rate_limited", str(exc))

    @app.exception_handler(EtherscanError)
    async def _etherscan(_: Request, exc: EtherscanError):
        return _err(502, "upstream_etherscan", str(exc))

    @app.exception_handler(AlchemyError)
    async def _alchemy(_: Request, exc: AlchemyError):
        return _err(502, "upstream_alchemy", str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return _err(
            422,
            "validation_error",
            "Request validation failed",
            details={"errors": exc.errors()},
        )

    @app.exception_handler(AegisError)
    async def _aegis_default(_: Request, exc: AegisError):
        return _err(exc.status_code, exc.code, str(exc) or exc.code)


def _err(
    status: int, code: str, message: str, details: dict | None = None
) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)
```

- [ ] **Step 5: Implement `backend/src/aegis/api/healthz.py`**

```python
"""Liveness endpoint."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Implement `backend/src/aegis/main.py`**

```python
"""FastAPI app factory + lifespan."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI, Request

from aegis.api import healthz
from aegis.api.errors import register_exception_handlers
from aegis.clients.alchemy import AlchemyClient
from aegis.clients.base import build_http_client
from aegis.clients.etherscan import EtherscanClient
from aegis.config import Settings, get_settings
from aegis.db import build_engine, build_sessionmaker, init_db
from aegis.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    app = FastAPI(title="Aegis Backend", version="0.1.0", lifespan=_lifespan)
    app.state.settings = settings
    register_exception_handlers(app)
    _register_request_id(app)
    app.include_router(healthz.router, prefix="/v1")
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings: Settings = app.state.settings

    engine = build_engine(settings.database_url)
    await init_db(engine)
    sessionmaker = build_sessionmaker(engine)

    http = build_http_client(timeout=settings.http_timeout_seconds)
    etherscan = EtherscanClient(http, settings.etherscan_api_key, settings.etherscan_base_url)
    alchemy = AlchemyClient(http, settings.alchemy_api_key, settings.alchemy_base_url_tmpl)

    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.http = http
    app.state.etherscan = etherscan
    app.state.alchemy = alchemy

    structlog.get_logger("aegis").info("startup_complete", env=settings.env)
    try:
        yield
    finally:
        await http.aclose()
        await engine.dispose()


def _register_request_id(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = request_id
        return response


app = create_app()
```

- [ ] **Step 7: Extend `backend/tests/conftest.py` with `settings`, `app`, `client` fixtures**

Replace `backend/tests/conftest.py` contents with:
```python
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
```

- [ ] **Step 8: Write tests `backend/tests/test_healthz.py`**

```python
"""Liveness test."""
from __future__ import annotations


async def test_healthz_returns_ok(client):
    resp = await client.get("/v1/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_healthz_request_id_header_present(client):
    resp = await client.get("/v1/healthz")
    assert resp.headers.get("x-request-id")


async def test_healthz_request_id_passes_through(client):
    resp = await client.get("/v1/healthz", headers={"x-request-id": "abc-123"})
    assert resp.headers["x-request-id"] == "abc-123"
```

- [ ] **Step 9: Write tests `backend/tests/test_errors.py`**

```python
"""Error handler shape tests."""
from __future__ import annotations

from fastapi import APIRouter

from aegis.errors import AegisError, ConfigError, NotFoundError
from aegis.eth import InvalidAddressError


def _attach_throwers(app):
    router = APIRouter()

    @router.get("/_test/invalid-address")
    async def _():
        raise InvalidAddressError("bad addr")

    @router.get("/_test/not-found")
    async def _():
        raise NotFoundError("missing")

    @router.get("/_test/not-configured")
    async def _():
        raise ConfigError("KEY missing")

    @router.get("/_test/aegis-default")
    async def _():
        raise AegisError("boom")

    app.include_router(router)


async def test_invalid_address_maps_to_422(app, client):
    _attach_throwers(app)
    resp = await client.get("/_test/invalid-address")
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "invalid_address"
    assert body["error"]["message"] == "bad addr"


async def test_not_found_maps_to_404(app, client):
    _attach_throwers(app)
    resp = await client.get("/_test/not-found")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_not_configured_maps_to_503(app, client):
    _attach_throwers(app)
    resp = await client.get("/_test/not-configured")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "not_configured"


async def test_aegis_default_uses_subclass_attrs(app, client):
    _attach_throwers(app)
    resp = await client.get("/_test/aegis-default")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
```

- [ ] **Step 10: Run tests**

```bash
uv run pytest tests/test_healthz.py tests/test_errors.py -v
```
Expected: 7 passed.

- [ ] **Step 11: Run full suite**

```bash
uv run pytest -q
uv run ruff check .
```
Expected: all green.

- [ ] **Step 12: Commit**

```bash
git add backend/src/aegis/errors.py backend/src/aegis/api/ \
        backend/src/aegis/main.py backend/tests/conftest.py \
        backend/tests/test_healthz.py backend/tests/test_errors.py
git commit -m "feat(backend): add FastAPI app skeleton, healthz, error handlers, request-id middleware"
```

---

## Task 11: Devices API endpoint

**Files:**
- Create: `backend/src/aegis/api/devices.py`
- Modify: `backend/src/aegis/main.py` (include router)
- Create: `backend/tests/test_devices_api.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_devices_api.py`**

```python
"""POST /v1/devices behavior."""
from __future__ import annotations

from sqlalchemy import select

from aegis.models import Device


async def test_create_device_returns_201_with_defaults(client):
    resp = await client.post("/v1/devices", json={"device_id": "dev-1"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "dev-1"
    assert body["tier"] == "free"
    assert body["push_token"] is None
    assert body["created_at"]
    assert body["updated_at"]


async def test_create_device_with_explicit_tier(client):
    resp = await client.post(
        "/v1/devices", json={"device_id": "dev-2", "tier": "pro", "push_token": "tok"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["tier"] == "pro"
    assert body["push_token"] == "tok"


async def test_create_device_invalid_tier_returns_422(client):
    resp = await client.post(
        "/v1/devices", json={"device_id": "dev-3", "tier": "enterprise"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_create_device_upsert_preserves_created_at(client, db_session):
    first = await client.post("/v1/devices", json={"device_id": "dev-4"})
    created_first = first.json()["created_at"]

    second = await client.post(
        "/v1/devices", json={"device_id": "dev-4", "tier": "pro", "push_token": "t2"}
    )
    assert second.status_code == 201
    body = second.json()
    assert body["created_at"] == created_first
    assert body["tier"] == "pro"
    assert body["push_token"] == "t2"
    assert body["updated_at"] >= created_first
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_devices_api.py -v
```
Expected: 404s on the POST (no router yet) or collection error.

- [ ] **Step 3: Implement `backend/src/aegis/api/devices.py`**

```python
"""Devices, addresses, scan endpoints."""
from __future__ import annotations

from fastapi import APIRouter, status

from aegis.api.deps import SessionDep
from aegis.models import Device
from aegis.schemas import DeviceCreate, DeviceOut

router = APIRouter()


@router.post(
    "/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED
)
async def create_device(body: DeviceCreate, session: SessionDep) -> Device:
    existing = await session.get(Device, body.device_id)
    if existing is None:
        device = Device(id=body.device_id, push_token=body.push_token, tier=body.tier)
        session.add(device)
    else:
        if body.push_token is not None:
            existing.push_token = body.push_token
        existing.tier = body.tier
        device = existing
    await session.commit()
    await session.refresh(device)
    return device
```

- [ ] **Step 4: Wire router in `backend/src/aegis/main.py`**

In `create_app`, after `app.include_router(healthz.router, prefix="/v1")`, add:
```python
    from aegis.api import devices

    app.include_router(devices.router, prefix="/v1")
```

(Move the import to the top of the file alongside `from aegis.api import healthz`.)

The final import line becomes:
```python
from aegis.api import devices, healthz
```

And the router include block becomes:
```python
    app.include_router(healthz.router, prefix="/v1")
    app.include_router(devices.router, prefix="/v1")
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run pytest tests/test_devices_api.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/src/aegis/api/devices.py backend/src/aegis/main.py \
        backend/tests/test_devices_api.py
git commit -m "feat(backend): add POST /v1/devices upsert"
```

---

## Task 12: Watched-addresses API endpoints

**Files:**
- Modify: `backend/src/aegis/api/devices.py` (add 3 endpoints)
- Create: `backend/tests/test_addresses_api.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_addresses_api.py`**

```python
"""POST/GET/DELETE /v1/devices/{id}/addresses behavior."""
from __future__ import annotations


VITALIK_MIXED = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
VITALIK_LOWER = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


async def _register(client, device_id: str = "dev"):
    await client.post("/v1/devices", json={"device_id": device_id})


async def test_add_address_normalizes_to_lowercase(client):
    await _register(client)
    resp = await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["address"] == VITALIK_LOWER
    assert body["chain"] == "ethereum"
    assert body["device_id"] == "dev"


async def test_add_address_rejects_bad_format(client):
    await _register(client)
    resp = await client.post(
        "/v1/devices/dev/addresses", json={"address": "not-an-address"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_add_address_idempotent(client):
    await _register(client)
    first = await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    second = await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_LOWER}
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


async def test_add_address_updates_nickname_on_reupsert(client):
    await _register(client)
    await client.post(
        "/v1/devices/dev/addresses",
        json={"address": VITALIK_MIXED, "nickname": "main"},
    )
    second = await client.post(
        "/v1/devices/dev/addresses",
        json={"address": VITALIK_LOWER, "nickname": "main-renamed"},
    )
    assert second.json()["nickname"] == "main-renamed"


async def test_add_address_unknown_device(client):
    resp = await client.post(
        "/v1/devices/missing/addresses", json={"address": VITALIK_MIXED}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_list_addresses(client):
    await _register(client)
    await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    resp = await client.get("/v1/devices/dev/addresses")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["addresses"]) == 1
    assert body["addresses"][0]["address"] == VITALIK_LOWER


async def test_list_addresses_unknown_device(client):
    resp = await client.get("/v1/devices/missing/addresses")
    assert resp.status_code == 404


async def test_delete_address(client):
    await _register(client)
    add_resp = await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    addr_id = add_resp.json()["id"]
    resp = await client.delete(f"/v1/devices/dev/addresses/{addr_id}")
    assert resp.status_code == 204
    list_resp = await client.get("/v1/devices/dev/addresses")
    assert list_resp.json()["addresses"] == []


async def test_delete_address_wrong_device(client):
    await _register(client, "dev-a")
    await _register(client, "dev-b")
    add_resp = await client.post(
        "/v1/devices/dev-a/addresses", json={"address": VITALIK_MIXED}
    )
    addr_id = add_resp.json()["id"]
    resp = await client.delete(f"/v1/devices/dev-b/addresses/{addr_id}")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_addresses_api.py -v
```
Expected: 404s / failing assertions because endpoints are missing.

- [ ] **Step 3: Add endpoints to `backend/src/aegis/api/devices.py`**

Append to existing file:
```python
from sqlalchemy import select

from aegis.errors import NotFoundError
from aegis.models import WatchedAddress
from aegis.schemas import AddressCreate, AddressList, AddressOut


@router.post(
    "/devices/{device_id}/addresses",
    response_model=AddressOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_address(
    device_id: str, body: AddressCreate, session: SessionDep
) -> WatchedAddress:
    device = await session.get(Device, device_id)
    if device is None:
        raise NotFoundError(f"Device {device_id!r} not found")
    stmt = select(WatchedAddress).where(
        WatchedAddress.device_id == device_id,
        WatchedAddress.address == body.address,
        WatchedAddress.chain == body.chain,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        if body.nickname is not None and existing.nickname != body.nickname:
            existing.nickname = body.nickname
            await session.commit()
            await session.refresh(existing)
        return existing
    addr = WatchedAddress(
        device_id=device_id,
        address=body.address,
        chain=body.chain,
        nickname=body.nickname,
    )
    session.add(addr)
    await session.commit()
    await session.refresh(addr)
    return addr


@router.get("/devices/{device_id}/addresses", response_model=AddressList)
async def list_addresses(device_id: str, session: SessionDep) -> AddressList:
    device = await session.get(Device, device_id)
    if device is None:
        raise NotFoundError(f"Device {device_id!r} not found")
    stmt = (
        select(WatchedAddress)
        .where(WatchedAddress.device_id == device_id)
        .order_by(WatchedAddress.id)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return AddressList(addresses=[AddressOut.model_validate(r) for r in rows])


@router.delete(
    "/devices/{device_id}/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_address(
    device_id: str, address_id: int, session: SessionDep
) -> None:
    addr = await session.get(WatchedAddress, address_id)
    if addr is None or addr.device_id != device_id:
        raise NotFoundError(
            f"Address {address_id} not found for device {device_id!r}"
        )
    await session.delete(addr)
    await session.commit()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_addresses_api.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/aegis/api/devices.py backend/tests/test_addresses_api.py
git commit -m "feat(backend): add watched-address POST/GET/DELETE endpoints"
```

---

## Task 13: Scan endpoint

**Files:**
- Modify: `backend/src/aegis/api/devices.py` (add scan endpoint)
- Create: `backend/tests/test_scan_api.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_scan_api.py`**

```python
"""POST /v1/devices/{id}/scan end-to-end."""
from __future__ import annotations

import json

from pytest_httpx import HTTPXMock

from tests.conftest import load_fixture

VITALIK_MIXED = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
USDC_LOWER = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT_LOWER = "0xdac17f958d2ee523a2206206994597c13d831ec7"


async def test_scan_returns_503_when_etherscan_key_missing(client, app):
    app.state.settings.etherscan_api_key = ""
    await client.post("/v1/devices", json={"device_id": "dev"})
    resp = await client.post("/v1/devices/dev/scan")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "not_configured"
    assert "ETHERSCAN_API_KEY" in body["error"]["message"]


async def test_scan_returns_503_when_alchemy_key_missing(client, app):
    app.state.settings.alchemy_api_key = ""
    await client.post("/v1/devices", json={"device_id": "dev"})
    resp = await client.post("/v1/devices/dev/scan")
    assert resp.status_code == 503
    assert "ALCHEMY_API_KEY" in resp.json()["error"]["message"]


async def test_scan_returns_404_for_missing_device(client):
    resp = await client.post("/v1/devices/missing/scan")
    assert resp.status_code == 404


async def test_scan_end_to_end_with_mocked_upstream(
    client, app, httpx_mock: HTTPXMock
):
    # The app's lifespan built its own httpx client; we mock by URL via pytest-httpx.
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(
        url__startswith="https://test-etherscan/api",
        json=load_fixture("etherscan_logs_simple.json"),
    )
    # Token metadata: USDC (symbol+decimals), USDT (symbol+decimals) — but
    # we don't know order. Use callback that branches on `data` selector.
    def _alchemy_callback(request):
        payload = json.loads(request.read())
        method = payload["method"]
        if method == "eth_call":
            data = payload["params"][0]["data"]
            to = payload["params"][0]["to"]
            if data == "0x95d89b41":  # symbol()
                if to == USDC_LOWER:
                    return httpx.Response(200, json=fixtures["symbol_usdc"])
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "result": "0x0000000000000000000000000000000000000000000000000000000000000020"
                        + "0000000000000000000000000000000000000000000000000000000000000004"
                        + "5553445400000000000000000000000000000000000000000000000000000000",
                    },
                )
            if data == "0x313ce567":  # decimals()
                return httpx.Response(200, json=fixtures["decimals_usdc"])
        return httpx.Response(500, json={"error": "unexpected"})

    import httpx
    httpx_mock.add_callback(_alchemy_callback, url__startswith="https://test-alchemy/")

    await client.post("/v1/devices", json={"device_id": "dev"})
    await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    resp = await client.post("/v1/devices/dev/scan")
    assert resp.status_code == 200
    body = resp.json()
    assert "approvals" in body
    by_token = {a["token"]["address"]: a for a in body["approvals"]}
    assert set(by_token.keys()) == {USDC_LOWER, USDT_LOWER}
    assert by_token[USDC_LOWER]["amount"] == "0"  # revoke wins
    assert by_token[USDT_LOWER]["amount"] == "100000000"
    assert by_token[USDC_LOWER]["token"]["symbol"] == "USDC"
    assert by_token[USDT_LOWER]["token"]["symbol"] == "USDT"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_scan_api.py -v
```
Expected: 404s / failing assertions.

- [ ] **Step 3: Add scan endpoint to `backend/src/aegis/api/devices.py`**

Append:
```python
from aegis.api.deps import AlchemyDep, EtherscanDep, SettingsDep
from aegis.errors import ConfigError
from aegis.models import Approval
from aegis.scanner import scan_wallet
from aegis.schemas import ApprovalList, ApprovalOut, TokenOut


@router.post("/devices/{device_id}/scan", response_model=ApprovalList)
async def scan_device(
    device_id: str,
    session: SessionDep,
    settings: SettingsDep,
    etherscan: EtherscanDep,
    alchemy: AlchemyDep,
) -> ApprovalList:
    if not settings.etherscan_api_key:
        raise ConfigError("ETHERSCAN_API_KEY missing")
    if not settings.alchemy_api_key:
        raise ConfigError("ALCHEMY_API_KEY missing")

    device = await session.get(Device, device_id)
    if device is None:
        raise NotFoundError(f"Device {device_id!r} not found")

    stmt = select(WatchedAddress).where(WatchedAddress.device_id == device_id)
    addresses = (await session.execute(stmt)).scalars().all()

    all_approvals: list[Approval] = []
    for addr in addresses:
        result = await scan_wallet(session, addr, etherscan, alchemy)
        all_approvals.extend(result)

    payload: list[ApprovalOut] = []
    for ap in all_approvals:
        await session.refresh(ap, attribute_names=["token"])
        payload.append(
            ApprovalOut(
                token=TokenOut.model_validate(ap.token),
                spender=ap.spender,
                amount=ap.amount,
                block_number=ap.block_number,
                tx_hash=ap.tx_hash,
                first_seen_at=ap.first_seen_at,
                last_seen_at=ap.last_seen_at,
            )
        )
    return ApprovalList(approvals=payload)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_scan_api.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Run full suite + ruff**

```bash
uv run pytest -q
uv run ruff check .
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/aegis/api/devices.py backend/tests/test_scan_api.py
git commit -m "feat(backend): add POST /v1/devices/{id}/scan endpoint"
```

---

## Task 14: APScheduler integration (`scheduler.py`)

**Files:**
- Create: `backend/src/aegis/scheduler.py`
- Modify: `backend/src/aegis/main.py` (wire scheduler in lifespan)
- Create: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_scheduler.py`**

```python
"""Tests for APScheduler wiring + scan_all_watched_addresses job."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from aegis.clients.alchemy import TokenMetadata
from aegis.clients.etherscan import ApprovalEvent
from aegis.config import Settings
from aegis.models import Device, WatchedAddress
from aegis.scheduler import build_scheduler, scan_all_watched_addresses


@pytest_asyncio.fixture
async def sessionmaker_fixture(engine) -> async_sessionmaker:
    from aegis.db import build_sessionmaker

    return build_sessionmaker(engine)


async def test_build_scheduler_registers_scan_all_job(sessionmaker_fixture):
    settings = Settings(scheduler_enabled=True, scan_interval_minutes=15, _env_file=None)
    etherscan = AsyncMock()
    alchemy = AsyncMock()
    scheduler = build_scheduler(settings, sessionmaker_fixture, etherscan, alchemy)
    job = scheduler.get_job("scan_all")
    assert job is not None


async def test_scan_all_watched_addresses_invokes_scan_for_each(
    sessionmaker_fixture,
):
    async with sessionmaker_fixture() as session:
        session.add(Device(id="d1"))
        session.add(Device(id="d2"))
        session.add(WatchedAddress(device_id="d1", address="0xa", chain="ethereum"))
        session.add(WatchedAddress(device_id="d2", address="0xb", chain="ethereum"))
        await session.commit()

    etherscan = AsyncMock()
    etherscan.get_approval_logs.return_value = []
    alchemy = AsyncMock()
    alchemy.get_erc20_metadata.return_value = TokenMetadata(symbol=None, decimals=None)

    await scan_all_watched_addresses(sessionmaker_fixture, etherscan, alchemy, concurrency=2)
    assert etherscan.get_approval_logs.call_count == 2


async def test_scan_all_watched_addresses_swallows_per_wallet_errors(
    sessionmaker_fixture,
):
    async with sessionmaker_fixture() as session:
        session.add(Device(id="d1"))
        session.add(WatchedAddress(device_id="d1", address="0xa", chain="ethereum"))
        session.add(WatchedAddress(device_id="d1", address="0xb", chain="ethereum"))
        await session.commit()

    etherscan = AsyncMock()

    async def maybe_fail(address):
        if address == "0xa":
            raise RuntimeError("boom")
        return [ApprovalEvent(token="0xt", spender="0xs", amount="1", block_number=1, tx_hash="0xtx", log_index=0)]

    etherscan.get_approval_logs.side_effect = maybe_fail
    alchemy = AsyncMock()
    alchemy.get_erc20_metadata.return_value = TokenMetadata(symbol=None, decimals=None)

    # Should not raise — failures logged + isolated per address
    await scan_all_watched_addresses(sessionmaker_fixture, etherscan, alchemy, concurrency=2)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_scheduler.py -v
```
Expected: collection error / `ModuleNotFoundError: No module named 'aegis.scheduler'`.

- [ ] **Step 3: Implement `backend/src/aegis/scheduler.py`**

```python
"""APScheduler setup + scan-all job."""
from __future__ import annotations

import asyncio

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from aegis.clients.alchemy import AlchemyClient
from aegis.clients.etherscan import EtherscanClient
from aegis.config import Settings
from aegis.models import WatchedAddress
from aegis.scanner import scan_wallet


def build_scheduler(
    settings: Settings,
    sessionmaker: async_sessionmaker,
    etherscan: EtherscanClient,
    alchemy: AlchemyClient,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scan_all_watched_addresses,
        trigger=IntervalTrigger(minutes=settings.scan_interval_minutes),
        args=[sessionmaker, etherscan, alchemy, settings.scan_concurrency],
        id="scan_all",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


async def scan_all_watched_addresses(
    sessionmaker: async_sessionmaker,
    etherscan: EtherscanClient,
    alchemy: AlchemyClient,
    concurrency: int = 4,
) -> None:
    log = structlog.get_logger("aegis.scheduler")
    semaphore = asyncio.Semaphore(concurrency)

    async with sessionmaker() as session:
        rows = (await session.execute(select(WatchedAddress))).scalars().all()
        ids = [r.id for r in rows]

    log.info("scan_tick_start", watched_count=len(ids))

    async def _one(addr_id: int) -> None:
        async with semaphore, sessionmaker() as session:
            addr = await session.get(WatchedAddress, addr_id)
            if addr is None:
                return
            try:
                await scan_wallet(session, addr, etherscan, alchemy)
            except Exception:  # noqa: BLE001
                log.exception("scan_wallet_failed", watched_address_id=addr_id)

    await asyncio.gather(*[_one(i) for i in ids])
    log.info("scan_tick_complete")
```

- [ ] **Step 4: Wire scheduler in `backend/src/aegis/main.py`**

In `_lifespan`, after `app.state.alchemy = alchemy`, add:
```python
    from aegis.scheduler import build_scheduler

    scheduler = None
    if settings.scheduler_enabled:
        scheduler = build_scheduler(settings, sessionmaker, etherscan, alchemy)
        scheduler.start()
    app.state.scheduler = scheduler
```

And in the `finally:` block, before `await http.aclose()`, add:
```python
        if scheduler is not None:
            scheduler.shutdown(wait=False)
```

Final `_lifespan` reads:
```python
@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings: Settings = app.state.settings

    engine = build_engine(settings.database_url)
    await init_db(engine)
    sessionmaker = build_sessionmaker(engine)

    http = build_http_client(timeout=settings.http_timeout_seconds)
    etherscan = EtherscanClient(http, settings.etherscan_api_key, settings.etherscan_base_url)
    alchemy = AlchemyClient(http, settings.alchemy_api_key, settings.alchemy_base_url_tmpl)

    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.http = http
    app.state.etherscan = etherscan
    app.state.alchemy = alchemy

    from aegis.scheduler import build_scheduler

    scheduler = None
    if settings.scheduler_enabled:
        scheduler = build_scheduler(settings, sessionmaker, etherscan, alchemy)
        scheduler.start()
    app.state.scheduler = scheduler

    structlog.get_logger("aegis").info("startup_complete", env=settings.env)
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        await http.aclose()
        await engine.dispose()
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run pytest tests/test_scheduler.py -v
uv run pytest -q
```
Expected: 3 new passing, full suite green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/aegis/scheduler.py backend/src/aegis/main.py \
        backend/tests/test_scheduler.py
git commit -m "feat(backend): wire APScheduler with 60-min scan-all tick"
```

---

## Task 15: Sentry observability (`observability.py`)

**Files:**
- Create: `backend/src/aegis/observability.py`
- Modify: `backend/src/aegis/main.py` (call `init_sentry`)
- Create: `backend/tests/test_observability.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_observability.py`**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_observability.py -v
```
Expected: `ModuleNotFoundError: No module named 'aegis.observability'`.

- [ ] **Step 3: Implement `backend/src/aegis/observability.py`**

```python
"""Sentry initialization (opt-in via SENTRY_DSN env)."""
from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from aegis.config import Settings


def init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        traces_sample_rate=0.0,
        send_default_pii=False,
        integrations=[
            FastApiIntegration(),
            AsyncioIntegration(),
            SqlalchemyIntegration(),
        ],
    )
```

- [ ] **Step 4: Call `init_sentry` from `create_app` in `backend/src/aegis/main.py`**

In `create_app`, after `configure_logging(...)`, add:
```python
    from aegis.observability import init_sentry

    init_sentry(settings)
```

Final `create_app` reads:
```python
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)
    from aegis.observability import init_sentry

    init_sentry(settings)

    app = FastAPI(title="Aegis Backend", version="0.1.0", lifespan=_lifespan)
    app.state.settings = settings
    register_exception_handlers(app)
    _register_request_id(app)
    app.include_router(healthz.router, prefix="/v1")
    app.include_router(devices.router, prefix="/v1")
    return app
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run pytest tests/test_observability.py -v
uv run pytest -q
```
Expected: 2 new passing, full suite green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/aegis/observability.py backend/src/aegis/main.py \
        backend/tests/test_observability.py
git commit -m "feat(backend): scaffold Sentry init (opt-in via SENTRY_DSN)"
```

---

## Task 16: Final verification, coverage gate, README finalize

**Files:**
- Modify: `backend/README.md` (final docs)

- [ ] **Step 1: Run the full test suite with coverage**

From `backend/`:
```bash
uv run pytest -q --cov=aegis --cov-report=term-missing --cov-fail-under=85
```
Expected: all tests pass; coverage ≥85%. If below, add focused tests for uncovered lines (most likely in `main.py` lifespan paths — covered indirectly by `app` fixture using `lifespan_context`).

- [ ] **Step 2: Run ruff lint + format check**

```bash
uv run ruff check .
uv run ruff format --check .
```
Expected: both clean. If format check fails, run `uv run ruff format .` and commit the format fixes separately.

- [ ] **Step 3: Smoke test the live server**

Create `.env`:
```bash
cp .env.example .env
```
Start the server (scheduler off to avoid loops without keys):
```bash
SCHEDULER_ENABLED=false uv run uvicorn aegis.main:app --port 8000 &
SERVER_PID=$!
sleep 2
```

- [ ] **Step 4: Verify healthz**

```bash
curl -s localhost:8000/v1/healthz
```
Expected output:
```json
{"status":"ok"}
```

- [ ] **Step 5: Verify device + address registration**

```bash
curl -s -X POST localhost:8000/v1/devices \
     -H 'content-type: application/json' \
     -d '{"device_id":"smoke-1"}'
curl -s -X POST localhost:8000/v1/devices/smoke-1/addresses \
     -H 'content-type: application/json' \
     -d '{"address":"0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}'
curl -s localhost:8000/v1/devices/smoke-1/addresses
```
Expected: 201s with payloads. Address is returned lowercase.

- [ ] **Step 6: Verify scan returns 503 without API keys**

```bash
curl -s -i -X POST localhost:8000/v1/devices/smoke-1/scan
```
Expected: `HTTP/1.1 503 ...` and body:
```json
{"error":{"code":"not_configured","message":"ETHERSCAN_API_KEY missing"}}
```

- [ ] **Step 7: Stop the server**

```bash
kill $SERVER_PID
wait $SERVER_PID 2>/dev/null || true
```

- [ ] **Step 8: Replace `backend/README.md` with the final version**

```markdown
# Aegis Backend (Week 1)

FastAPI service that monitors EVM wallets for risky ERC-20 approvals.
Week 1 scope: Ethereum mainnet, Etherscan + Alchemy.

See [`docs/superpowers/specs/2026-05-11-aegis-week1-backend-design.md`](../docs/superpowers/specs/2026-05-11-aegis-week1-backend-design.md) for the design.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Free API keys: [Etherscan](https://etherscan.io/myapikey), [Alchemy](https://dashboard.alchemy.com/)

## Setup

```bash
cd backend
uv sync --all-extras
cp .env.example .env  # then fill in ETHERSCAN_API_KEY and ALCHEMY_API_KEY
```

## Run

```bash
uv run uvicorn aegis.main:app --reload --port 8000
```

A scheduled scan runs every `SCAN_INTERVAL_MINUTES` (default 60) across every watched address. Set `SCHEDULER_ENABLED=false` to disable.

## API (v1)

| Method | Path | Body |
|---|---|---|
| GET | `/v1/healthz` | — |
| POST | `/v1/devices` | `{"device_id":"...","push_token"?:"...","tier"?:"free"|"pro"}` |
| POST | `/v1/devices/{id}/addresses` | `{"address":"0x...","chain"?:"ethereum","nickname"?:"..."}` |
| GET | `/v1/devices/{id}/addresses` | — |
| DELETE | `/v1/devices/{id}/addresses/{addr_id}` | — |
| POST | `/v1/devices/{id}/scan` | — |

Errors are JSON: `{"error":{"code":"...","message":"..."}}`.

## Configuration

All settings are environment-driven (see `.env.example`):

| Env var | Default |
|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./aegis.db` |
| `ETHERSCAN_API_KEY` | — (required for `/scan`) |
| `ALCHEMY_API_KEY` | — (required for `/scan`) |
| `LOG_LEVEL` | `INFO` |
| `LOG_FORMAT` | `console` (or `json`) |
| `SCHEDULER_ENABLED` | `true` |
| `SCAN_INTERVAL_MINUTES` | `60` |
| `SCAN_CONCURRENCY` | `4` |
| `HTTP_TIMEOUT_SECONDS` | `10` |
| `SENTRY_DSN` | — (empty disables) |
| `ENV` | `development` |

## Test

```bash
uv run pytest -q                                # run all tests
uv run pytest -q --cov=aegis --cov-fail-under=85  # with coverage gate
uv run ruff check .                             # lint
uv run ruff format --check .                    # format
```

All outbound HTTP is mocked via `pytest-httpx`; tests don't hit Etherscan or Alchemy.

## Project layout

```
src/aegis/
├── api/        # FastAPI routers + DI + error handlers
├── clients/    # Etherscan + Alchemy HTTP clients
├── eth.py      # APPROVAL_TOPIC, address helpers
├── scanner.py  # scan_wallet + per-wallet lock
├── scheduler.py# APScheduler scan-all tick
├── models.py   # SQLAlchemy ORM
├── schemas.py  # Pydantic I/O + EthAddress type
├── db.py       # Async engine + WAL pragma
├── config.py   # pydantic-settings
├── logging.py  # structlog config
├── observability.py  # Sentry opt-in
├── errors.py   # AegisError, NotFoundError, ConfigError
└── main.py     # App factory + lifespan + request-id middleware
```
```

- [ ] **Step 9: Commit + push**

From repo root:
```bash
git add backend/README.md
git commit -m "docs(backend): finalize week-1 README"
git push -u origin claude/read-aegis-artifact-j46Ss
```

---

## Self-review (already executed during plan authoring)

**Spec coverage:** every spec section has at least one task — §1 architecture (Task 10 wiring), §2 layout (Task 1), §3 data model (Task 5), §4 API (Tasks 10-13), §5 scanner (Task 9), §6 clients (Tasks 7-8), §7 scheduler (Task 14), §8 logging/observability (Tasks 4, 15), §9 errors (Task 10), §10 config (Task 3), §11 testing (every task includes tests), §12 verification (Task 16), §13 out-of-scope honored.

**Placeholders:** none. Every code block is complete. No "TBD" or "similar to Task N".

**Type consistency:** method names match across tasks — `scan_wallet`, `get_approval_logs`, `get_erc20_metadata`, `eth_call`, `eth_block_number`, `normalize_address`, `pad_address_to_topic`, `build_engine`, `build_sessionmaker`, `init_db`, `build_http_client`, `http_retry`, `register_exception_handlers`, `configure_logging`, `init_sentry`, `build_scheduler`, `scan_all_watched_addresses`. `ApprovalEvent`, `TokenMetadata`, `Device`, `WatchedAddress`, `Token`, `Approval` are referenced with consistent fields. `EtherscanError` / `RateLimitedError` / `AlchemyError` / `AegisError` / `NotFoundError` / `ConfigError` / `InvalidAddressError` declared in Tasks 2/7/8/10 and consumed only after declaration. Settings field names match between `config.py` (Task 3), `.env.example` (Task 1), and consumers (Tasks 8-15).
