"""Tests for aegis.eth helpers."""
from __future__ import annotations

import pytest

from aegis.eth import (
    APPROVAL_TOPIC,
    InvalidAddressError,
    normalize_address,
    pad_address_to_topic,
)

KNOWN_APPROVAL_TOPIC = (
    "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
)
VITALIK = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
VITALIK_LOWER = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


def test_approval_topic_matches_known_keccak():
    assert APPROVAL_TOPIC == KNOWN_APPROVAL_TOPIC


def test_normalize_address_lowercases_eip55_mixed_case():
    assert normalize_address(VITALIK) == VITALIK_LOWER


def test_normalize_address_passes_lowercase_unchanged():
    assert normalize_address(VITALIK_LOWER) == VITALIK_LOWER


def test_normalize_address_rejects_garbage():
    with pytest.raises(InvalidAddressError):
        normalize_address("hello world")


def test_normalize_address_rejects_short_hex():
    with pytest.raises(InvalidAddressError):
        normalize_address("0x1234")


def test_normalize_address_rejects_non_string():
    with pytest.raises(InvalidAddressError):
        normalize_address(123)  # type: ignore[arg-type]


def test_pad_address_to_topic_produces_32_bytes():
    topic = pad_address_to_topic(VITALIK)
    assert topic == "0x000000000000000000000000d8da6bf26964af9d7eed9e03e53415d37aa96045"
    assert len(topic) == 66  # "0x" + 64 hex chars
