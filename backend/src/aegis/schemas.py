"""Pydantic I/O schemas + EthAddress type."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

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
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
