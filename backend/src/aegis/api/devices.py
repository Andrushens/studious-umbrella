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
