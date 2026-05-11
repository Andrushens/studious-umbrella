"""Alchemy JSON-RPC client + ERC-20 metadata helper."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from aegis.clients.base import http_retry


class AlchemyError(RuntimeError):
    """Alchemy responded with an error object or unexpected payload."""


@dataclass(frozen=True, slots=True)
class TokenMetadata:
    symbol: str | None
    decimals: int | None
    name: str | None = None


SYMBOL_SELECTOR = "0x95d89b41"
DECIMALS_SELECTOR = "0x313ce567"


class AlchemyClient:
    def __init__(
        self, http: httpx.AsyncClient, api_key: str, base_url_tmpl: str
    ) -> None:
        self._http = http
        self._url = base_url_tmpl.format(api_key=api_key)

    @http_retry
    async def _post(self, payload: dict) -> dict:
        resp = await self._http.post(self._url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def _rpc(self, method: str, params: list) -> object:
        body = await self._post(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        )
        if "error" in body:
            raise AlchemyError(body["error"].get("message", "Alchemy RPC error"))
        return body["result"]

    async def eth_block_number(self) -> int:
        result = await self._rpc("eth_blockNumber", [])
        assert isinstance(result, str)
        return int(result, 16)

    async def eth_call(self, to: str, data: str, block: str = "latest") -> str:
        result = await self._rpc("eth_call", [{"to": to, "data": data}, block])
        assert isinstance(result, str)
        return result

    async def get_erc20_metadata(self, token_address: str) -> TokenMetadata:
        symbol = await self._try_call(token_address, SYMBOL_SELECTOR, _decode_string)
        decimals = await self._try_call(
            token_address, DECIMALS_SELECTOR, _decode_uint8
        )
        return TokenMetadata(symbol=symbol, decimals=decimals)

    async def _try_call(self, to: str, data: str, decoder):
        try:
            raw = await self.eth_call(to, data)
        except AlchemyError:
            return None
        if not raw or raw == "0x":
            return None
        try:
            return decoder(raw)
        except (ValueError, IndexError, UnicodeDecodeError):
            return None


def _decode_string(hex_data: str) -> str:
    """Decode a Solidity-encoded `string` return value.

    Handles both ABI-encoded dynamic strings (offset+length+bytes) and the
    legacy `bytes32` form used by tokens like MKR.
    """
    raw = bytes.fromhex(hex_data[2:])
    if len(raw) == 32:
        return raw.rstrip(b"\x00").decode("utf-8", errors="replace")
    length = int.from_bytes(raw[32:64], "big")
    return raw[64 : 64 + length].decode("utf-8", errors="replace")


def _decode_uint8(hex_data: str) -> int:
    return int(hex_data, 16) & 0xFF
