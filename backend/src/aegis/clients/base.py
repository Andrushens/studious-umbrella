"""Shared HTTP client utilities — factory + tenacity retry."""
from __future__ import annotations

import httpx
import tenacity


def build_http_client(timeout: float = 10.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout, http2=True)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


http_retry = tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=0.5, max=4),
    retry=tenacity.retry_if_exception(_is_retryable),
    reraise=True,
)
