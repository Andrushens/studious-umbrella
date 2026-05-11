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


def test_eth_address_rejects_non_string():
    with pytest.raises(ValidationError):
        _Wrap(addr=None)  # type: ignore[arg-type]


def test_approval_out_round_trip_from_attributes():
    """ApprovalOut.model_validate works on an ORM-like object with a nested .token."""
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from aegis.schemas import ApprovalOut

    now = datetime(2026, 5, 11, tzinfo=UTC)
    fake_token = SimpleNamespace(
        chain="ethereum",
        address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        symbol="USDC",
        decimals=6,
        name=None,
    )
    fake_approval = SimpleNamespace(
        token=fake_token,
        spender="0x1111111254eeb25477b68fb85ed929f73a960582",
        amount="123",
        block_number=42,
        tx_hash="0xdeadbeef",
        first_seen_at=now,
        last_seen_at=now,
    )
    out = ApprovalOut.model_validate(fake_approval)
    assert out.token.symbol == "USDC"
    assert out.token.decimals == 6
    assert out.spender == "0x1111111254eeb25477b68fb85ed929f73a960582"
    assert out.amount == "123"
    assert out.first_seen_at == now
