"""POST /v1/devices/{id}/scan end-to-end."""
from __future__ import annotations

import json
import re

import httpx
from pytest_httpx import HTTPXMock

from tests.conftest import load_fixture

VITALIK_MIXED = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
USDC_LOWER = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT_LOWER = "0xdac17f958d2ee523a2206206994597c13d831ec7"

ETHERSCAN_RE = re.compile(re.escape("https://test-etherscan/api"))
ALCHEMY_RE = re.compile(re.escape("https://test-alchemy/"))


async def test_scan_returns_503_when_etherscan_key_missing(client, app):
    app.state.settings.etherscan_api_key = ""
    await client.post("/v1/devices", json={"device_id": "dev"})
    resp = await client.post("/v1/devices/dev/scan")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "not_configured"
    assert "ETHERSCAN_API_KEY" in body["error"]["message"]


async def test_scan_returns_503_when_alchemy_key_missing(client, app):
    app.state.settings.alchemy_api_key = ""
    await client.post("/v1/devices", json={"device_id": "dev"})
    resp = await client.post("/v1/devices/dev/scan")
    assert resp.status_code == 503
    assert "ALCHEMY_API_KEY" in resp.json()["error"]["message"]


async def test_scan_returns_404_for_missing_device(client):
    resp = await client.post("/v1/devices/missing/scan")
    assert resp.status_code == 404


async def test_scan_end_to_end_with_mocked_upstream(
    client, app, httpx_mock: HTTPXMock
):
    fixtures = load_fixture("alchemy_token_metadata.json")

    # Etherscan: return the 3-log fixture
    httpx_mock.add_response(
        url=ETHERSCAN_RE,
        json=load_fixture("etherscan_logs_simple.json"),
        is_reusable=True,
    )

    # Alchemy: callback that decodes the eth_call and returns symbol/decimals for USDC and USDT.
    usdt_symbol_hex = (
        "0x0000000000000000000000000000000000000000000000000000000000000020"
        "0000000000000000000000000000000000000000000000000000000000000004"
        "5553445400000000000000000000000000000000000000000000000000000000"
    )

    def alchemy_callback(request):
        payload = json.loads(request.read())
        method = payload["method"]
        if method == "eth_call":
            data = payload["params"][0]["data"]
            to = payload["params"][0]["to"].lower()
            if data == "0x95d89b41":  # symbol()
                if to == USDC_LOWER:
                    return httpx.Response(200, json=fixtures["symbol_usdc"])
                if to == USDT_LOWER:
                    return httpx.Response(
                        200,
                        json={"jsonrpc": "2.0", "id": 1, "result": usdt_symbol_hex},
                    )
            if data == "0x313ce567":  # decimals()
                return httpx.Response(200, json=fixtures["decimals_usdc"])
        return httpx.Response(500, json={"error": "unexpected"})

    httpx_mock.add_callback(alchemy_callback, url=ALCHEMY_RE, is_reusable=True)

    await client.post("/v1/devices", json={"device_id": "dev"})
    await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    resp = await client.post("/v1/devices/dev/scan")
    assert resp.status_code == 200
    body = resp.json()
    assert "approvals" in body
    by_token = {a["token"]["address"]: a for a in body["approvals"]}
    assert set(by_token.keys()) == {USDC_LOWER, USDT_LOWER}
    assert by_token[USDC_LOWER]["amount"] == "0"  # revoke wins
    assert by_token[USDT_LOWER]["amount"] == "100000000000000000"
    assert by_token[USDC_LOWER]["token"]["symbol"] == "USDC"
    assert by_token[USDT_LOWER]["token"]["symbol"] == "USDT"
