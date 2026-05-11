"""Wallet scanner — pulls Approval logs, upserts current allowances + token metadata."""
from __future__ import annotations

import asyncio
import weakref
from collections.abc import Iterable
from datetime import UTC, datetime

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
    now = datetime.now(UTC)
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
