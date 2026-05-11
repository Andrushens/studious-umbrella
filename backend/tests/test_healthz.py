"""Liveness test."""
from __future__ import annotations


async def test_healthz_returns_ok(client):
    resp = await client.get("/v1/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_healthz_request_id_header_present(client):
    resp = await client.get("/v1/healthz")
    assert resp.headers.get("x-request-id")


async def test_healthz_request_id_passes_through(client):
    resp = await client.get("/v1/healthz", headers={"x-request-id": "abc-123"})
    assert resp.headers["x-request-id"] == "abc-123"
