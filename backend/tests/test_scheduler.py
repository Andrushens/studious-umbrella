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
        return [
            ApprovalEvent(
                token="0xt", spender="0xs", amount="1", block_number=1, tx_hash="0xtx", log_index=0
            )
        ]

    etherscan.get_approval_logs.side_effect = maybe_fail
    alchemy = AsyncMock()
    alchemy.get_erc20_metadata.return_value = TokenMetadata(symbol=None, decimals=None)

    # Should not raise — failures logged + isolated per address
    await scan_all_watched_addresses(sessionmaker_fixture, etherscan, alchemy, concurrency=2)
