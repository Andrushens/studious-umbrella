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
