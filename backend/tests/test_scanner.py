"""Tests for scanner.scan_wallet."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

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
        ApprovalEvent(
            token=USDC, spender=SPENDER_A, amount="4294967295",
            block_number=0x100, tx_hash="0xaaaa1", log_index=0,
        ),
        ApprovalEvent(
            token=USDT, spender=SPENDER_B, amount="100000000",
            block_number=0x101, tx_hash="0xbbbb1", log_index=1,
        ),
        ApprovalEvent(
            token=USDC, spender=SPENDER_A, amount="0",
            block_number=0x102, tx_hash="0xaaaa2", log_index=0,
        ),
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
    # Second scan: only previously seen tokens; metadata not refetched
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
