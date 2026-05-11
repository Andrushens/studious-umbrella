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
