"""POST /v1/devices behavior."""
from __future__ import annotations


async def test_create_device_returns_201_with_defaults(client):
    resp = await client.post("/v1/devices", json={"device_id": "dev-1"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "dev-1"
    assert body["tier"] == "free"
    assert body["push_token"] is None
    assert body["created_at"]
    assert body["updated_at"]


async def test_create_device_with_explicit_tier(client):
    resp = await client.post(
        "/v1/devices", json={"device_id": "dev-2", "tier": "pro", "push_token": "tok"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["tier"] == "pro"
    assert body["push_token"] == "tok"


async def test_create_device_invalid_tier_returns_422(client):
    resp = await client.post(
        "/v1/devices", json={"device_id": "dev-3", "tier": "enterprise"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_create_device_upsert_preserves_created_at(client, db_session):
    first = await client.post("/v1/devices", json={"device_id": "dev-4"})
    created_first = first.json()["created_at"]

    second = await client.post(
        "/v1/devices", json={"device_id": "dev-4", "tier": "pro", "push_token": "t2"}
    )
    assert second.status_code == 201
    body = second.json()
    assert body["created_at"] == created_first
    assert body["tier"] == "pro"
    assert body["push_token"] == "t2"
    assert body["updated_at"] >= created_first
