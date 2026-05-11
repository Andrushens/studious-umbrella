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
