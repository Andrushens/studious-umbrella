"""Tests for Etherscan client (Approval-event getLogs)."""
from __future__ import annotations

import re

import httpx
import pytest
from pytest_httpx import HTTPXMock

from aegis.clients.etherscan import (
    ApprovalEvent,
    EtherscanClient,
    EtherscanError,
    RateLimitedError,
)
from tests.conftest import load_fixture

BASE_URL = "https://test-etherscan/api"
OWNER = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

_BASE_URL_RE = re.compile(re.escape(BASE_URL))


def _client() -> EtherscanClient:
    return EtherscanClient(
        httpx.AsyncClient(timeout=5.0),
        api_key="test-key",
        base_url=BASE_URL,
    )


async def test_get_approval_logs_parses_three_events(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_BASE_URL_RE, json=load_fixture("etherscan_logs_simple.json"))
    es = _client()
    events = await es.get_approval_logs(OWNER)
    assert len(events) == 3
    assert events[0].token == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert events[0].spender == "0x1111111254eeb25477b68fb85ed929f73a960582"
    assert events[0].amount == "4294967295"
    assert events[0].block_number == 0x100
    assert events[0].tx_hash == "0xaaaa1"
    assert events[2].amount == "0"


async def test_get_approval_logs_builds_correct_params(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_BASE_URL_RE, json={"status": "1", "message": "OK", "result": []})
    es = _client()
    await es.get_approval_logs(OWNER, from_block=100, to_block=200)
    request = httpx_mock.get_request()
    assert request is not None
    qp = dict(request.url.params)
    assert qp["module"] == "logs"
    assert qp["action"] == "getLogs"
    assert qp["topic0"] == "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
    assert qp["topic1"] == "0x000000000000000000000000d8da6bf26964af9d7eed9e03e53415d37aa96045"
    assert qp["fromBlock"] == "100"
    assert qp["toBlock"] == "200"
    assert qp["apikey"] == "test-key"
    assert qp["offset"] == "1000"
    assert qp["page"] == "1"


async def test_get_approval_logs_empty_returns_empty_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_BASE_URL_RE, json=load_fixture("etherscan_logs_empty.json"))
    es = _client()
    assert await es.get_approval_logs(OWNER) == []


async def test_get_approval_logs_paginates(httpx_mock: HTTPXMock):
    page1_logs = load_fixture("etherscan_logs_simple.json")["result"]
    big_page = {"status": "1", "message": "OK", "result": [page1_logs[0]] * 1000}
    httpx_mock.add_response(url=_BASE_URL_RE, json=big_page)
    page2 = {"status": "1", "message": "OK", "result": [page1_logs[1]]}
    httpx_mock.add_response(url=_BASE_URL_RE, json=page2)
    es = _client()
    events = await es.get_approval_logs(OWNER)
    assert len(events) == 1001
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert dict(requests[0].url.params)["page"] == "1"
    assert dict(requests[1].url.params)["page"] == "2"


async def test_get_approval_logs_rate_limited(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=_BASE_URL_RE,
        json={
            "status": "0",
            "message": "Max rate limit reached",
            "result": "Max rate limit reached",
        },
    )
    es = _client()
    with pytest.raises(RateLimitedError):
        await es.get_approval_logs(OWNER)


async def test_get_approval_logs_other_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=_BASE_URL_RE,
        json={"status": "0", "message": "NOTOK", "result": "Invalid API Key"},
    )
    es = _client()
    with pytest.raises(EtherscanError):
        await es.get_approval_logs(OWNER)


def test_approval_event_is_frozen_dataclass():
    ev = ApprovalEvent(
        token="0xa", spender="0xb", amount="0", block_number=1, tx_hash="0xtx", log_index=0
    )
    with pytest.raises(AttributeError):
        ev.amount = "100"  # type: ignore[misc]
