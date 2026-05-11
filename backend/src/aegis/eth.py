"""Ethereum helpers: event topics, address validation/normalization."""
from __future__ import annotations

from eth_utils import is_address, keccak


class InvalidAddressError(ValueError):
    """Raised when an input string is not a valid Ethereum address."""


APPROVAL_TOPIC = "0x" + keccak(text="Approval(address,address,uint256)").hex()


def normalize_address(value: object) -> str:
    """Return lowercase 0x-prefixed address; raise InvalidAddressError on bad input."""
    if not isinstance(value, str) or not is_address(value):
        raise InvalidAddressError(f"Not a valid Ethereum address: {value!r}")
    return value.lower()


def pad_address_to_topic(address: str) -> str:
    """Return 0x-prefixed 32-byte hex topic from an address (for eth_getLogs topicN)."""
    normalized = normalize_address(address)
    hex_part = normalized[2:].rjust(64, "0")
    return "0x" + hex_part
