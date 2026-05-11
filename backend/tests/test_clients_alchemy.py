"""Tests for Alchemy JSON-RPC client."""
from __future__ import annotations

import json as _json
import re

import httpx
import pytest
from pytest_httpx import HTTPXMock

from aegis.clients.alchemy import (
    AlchemyClient,
    AlchemyError,
    TokenMetadata,
)
from tests.conftest import load_fixture

BASE_TMPL = "https://test-alchemy/{api_key}"
ALCHEMY_URL = "https://test-alchemy/test-alchemy-key"
ALCHEMY_URL_RE = re.compile(re.escape(ALCHEMY_URL))
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def _client() -> AlchemyClient:
    return AlchemyClient(
        httpx.AsyncClient(timeout=5.0),
        api_key="test-alchemy-key",
        base_url_tmpl=BASE_TMPL,
    )


async def test_eth_block_number(httpx_mock: HTTPXMock):
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(url=ALCHEMY_URL_RE, json=fixtures["block_number"])
    c = _client()
    bn = await c.eth_block_number()
    assert bn == 0x10C8A47


async def test_eth_call_payload_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=ALCHEMY_URL_RE,
        json={"jsonrpc": "2.0", "id": 1, "result": "0xdeadbeef"},
    )
    c = _client()
    result = await c.eth_call(USDC, "0x95d89b41")
    assert result == "0xdeadbeef"
    req = httpx_mock.get_request()
    body = req.read()
    payload = _json.loads(body)
    assert payload["jsonrpc"] == "2.0"
    assert payload["method"] == "eth_call"
    assert payload["params"][0] == {"to": USDC, "data": "0x95d89b41"}
    assert payload["params"][1] == "latest"


async def test_eth_call_raises_on_rpc_error(httpx_mock: HTTPXMock):
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(url=ALCHEMY_URL_RE, json=fixtures["rpc_error"])
    c = _client()
    with pytest.raises(AlchemyError):
        await c.eth_call(USDC, "0x95d89b41")


async def test_get_erc20_metadata_decodes_string_and_uint8(httpx_mock: HTTPXMock):
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(url=ALCHEMY_URL_RE, json=fixtures["symbol_usdc"])
    httpx_mock.add_response(url=ALCHEMY_URL_RE, json=fixtures["decimals_usdc"])
    c = _client()
    meta = await c.get_erc20_metadata(USDC)
    assert meta == TokenMetadata(symbol="USDC", decimals=6, name=None)


async def test_get_erc20_metadata_falls_back_on_revert(httpx_mock: HTTPXMock):
    fixtures = load_fixture("alchemy_token_metadata.json")
    httpx_mock.add_response(url=ALCHEMY_URL_RE, json=fixtures["rpc_error"])
    httpx_mock.add_response(url=ALCHEMY_URL_RE, json=fixtures["rpc_error"])
    c = _client()
    meta = await c.get_erc20_metadata(USDC)
    assert meta.symbol is None
    assert meta.decimals is None
