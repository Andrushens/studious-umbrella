"""POST/GET/DELETE /v1/devices/{id}/addresses behavior."""
from __future__ import annotations

VITALIK_MIXED = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
VITALIK_LOWER = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


async def _register(client, device_id: str = "dev"):
    await client.post("/v1/devices", json={"device_id": device_id})


async def test_add_address_normalizes_to_lowercase(client):
    await _register(client)
    resp = await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["address"] == VITALIK_LOWER
    assert body["chain"] == "ethereum"
    assert body["device_id"] == "dev"


async def test_add_address_rejects_bad_format(client):
    await _register(client)
    resp = await client.post(
        "/v1/devices/dev/addresses", json={"address": "not-an-address"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_add_address_idempotent(client):
    await _register(client)
    first = await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    second = await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_LOWER}
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


async def test_add_address_updates_nickname_on_reupsert(client):
    await _register(client)
    await client.post(
        "/v1/devices/dev/addresses",
        json={"address": VITALIK_MIXED, "nickname": "main"},
    )
    second = await client.post(
        "/v1/devices/dev/addresses",
        json={"address": VITALIK_LOWER, "nickname": "main-renamed"},
    )
    assert second.json()["nickname"] == "main-renamed"


async def test_add_address_unknown_device(client):
    resp = await client.post(
        "/v1/devices/missing/addresses", json={"address": VITALIK_MIXED}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_list_addresses(client):
    await _register(client)
    await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    resp = await client.get("/v1/devices/dev/addresses")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["addresses"]) == 1
    assert body["addresses"][0]["address"] == VITALIK_LOWER


async def test_list_addresses_unknown_device(client):
    resp = await client.get("/v1/devices/missing/addresses")
    assert resp.status_code == 404


async def test_delete_address(client):
    await _register(client)
    add_resp = await client.post(
        "/v1/devices/dev/addresses", json={"address": VITALIK_MIXED}
    )
    addr_id = add_resp.json()["id"]
    resp = await client.delete(f"/v1/devices/dev/addresses/{addr_id}")
    assert resp.status_code == 204
    list_resp = await client.get("/v1/devices/dev/addresses")
    assert list_resp.json()["addresses"] == []


async def test_delete_address_wrong_device(client):
    await _register(client, "dev-a")
    await _register(client, "dev-b")
    add_resp = await client.post(
        "/v1/devices/dev-a/addresses", json={"address": VITALIK_MIXED}
    )
    addr_id = add_resp.json()["id"]
    resp = await client.delete(f"/v1/devices/dev-b/addresses/{addr_id}")
    assert resp.status_code == 404
