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
