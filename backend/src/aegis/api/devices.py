"""Devices, addresses, scan endpoints."""
from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import select

from aegis.api.deps import AlchemyDep, EtherscanDep, SessionDep, SettingsDep
from aegis.errors import ConfigError, NotFoundError
from aegis.models import Approval, Device, WatchedAddress
from aegis.scanner import scan_wallet
from aegis.schemas import (
    AddressCreate,
    AddressList,
    AddressOut,
    ApprovalList,
    ApprovalOut,
    DeviceCreate,
    DeviceOut,
    TokenOut,
)

router = APIRouter()


@router.post(
    "/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED
)
async def create_device(body: DeviceCreate, session: SessionDep) -> Device:
    existing = await session.get(Device, body.device_id)
    if existing is None:
        device = Device(
            id=body.device_id,
            push_token=body.push_token,
            tier=body.tier or "free",
        )
        session.add(device)
    else:
        if body.push_token is not None:
            existing.push_token = body.push_token
        if body.tier is not None:
            existing.tier = body.tier
        device = existing
    await session.commit()
    await session.refresh(device)
    return device


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
        await session.refresh(ap, attribute_names=["token", "watched_address"])
        payload.append(
            ApprovalOut(
                token=TokenOut.model_validate(ap.token),
                wallet_address=ap.watched_address.address,
                spender=ap.spender,
                amount=ap.amount,
                block_number=ap.block_number,
                tx_hash=ap.tx_hash,
                first_seen_at=ap.first_seen_at,
                last_seen_at=ap.last_seen_at,
            )
        )
    return ApprovalList(approvals=payload)
