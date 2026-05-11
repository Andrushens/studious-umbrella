"""Etherscan API client — getLogs for ERC-20 Approval events."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from aegis.clients.base import http_retry
from aegis.eth import APPROVAL_TOPIC, normalize_address, pad_address_to_topic


class EtherscanError(RuntimeError):
    """Etherscan responded with a non-success status."""


class RateLimitedError(EtherscanError):
    """Etherscan rate limit was hit."""


@dataclass(frozen=True, slots=True)
class ApprovalEvent:
    token: str
    spender: str
    amount: str
    block_number: int
    tx_hash: str
    log_index: int


class EtherscanClient:
    PAGE_SIZE = 1000

    def __init__(self, http: httpx.AsyncClient, api_key: str, base_url: str) -> None:
        self._http = http
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def get_approval_logs(
        self,
        owner: str,
        from_block: int = 0,
        to_block: int | str = "latest",
    ) -> list[ApprovalEvent]:
        owner_topic = pad_address_to_topic(owner)
        events: list[ApprovalEvent] = []
        page = 1
        while True:
            params = {
                "module": "logs",
                "action": "getLogs",
                "fromBlock": from_block,
                "toBlock": to_block,
                "topic0": APPROVAL_TOPIC,
                "topic1": owner_topic,
                "page": page,
                "offset": self.PAGE_SIZE,
                "apikey": self._api_key,
            }
            body = await self._fetch(params)
            status = str(body.get("status", "1"))
            message = body.get("message", "")
            result = body.get("result")

            if status == "0":
                if message == "No records found":
                    return events
                if isinstance(message, str) and "rate limit" in message.lower():
                    raise RateLimitedError(message)
                raise EtherscanError(f"Etherscan error: {message} ({result})")

            if not isinstance(result, list):
                raise EtherscanError(f"Unexpected Etherscan result: {result!r}")

            for log in result:
                events.append(self._parse_log(log))

            if len(result) < self.PAGE_SIZE:
                return events
            page += 1

    @http_retry
    async def _fetch(self, params: dict) -> dict:
        resp = await self._http.get(self._base_url, params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse_log(log: dict) -> ApprovalEvent:
        topics = log.get("topics") or []
        if len(topics) < 3:
            raise EtherscanError(
                f"Malformed Approval log: expected 3 topics, got {len(topics)}: {log!r}"
            )
        spender = "0x" + topics[2][-40:]
        data = log.get("data") or "0x"
        amount_int = int(data, 16) if data != "0x" else 0
        return ApprovalEvent(
            token=normalize_address(log["address"]),
            spender=normalize_address(spender),
            amount=str(amount_int),
            block_number=int(log["blockNumber"], 16),
            tx_hash=log["transactionHash"],
            log_index=int(log["logIndex"], 16),
        )
