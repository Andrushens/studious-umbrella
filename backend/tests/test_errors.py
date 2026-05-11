"""Error handler shape tests."""
from __future__ import annotations

from fastapi import APIRouter

from aegis.errors import AegisError, ConfigError, NotFoundError
from aegis.eth import InvalidAddressError


def _attach_throwers(app):
    router = APIRouter()

    @router.get("/_test/invalid-address")
    async def _():
        raise InvalidAddressError("bad addr")

    @router.get("/_test/not-found")
    async def _():
        raise NotFoundError("missing")

    @router.get("/_test/not-configured")
    async def _():
        raise ConfigError("KEY missing")

    @router.get("/_test/aegis-default")
    async def _():
        raise AegisError("boom")

    app.include_router(router)


async def test_invalid_address_maps_to_422(app, client):
    _attach_throwers(app)
    resp = await client.get("/_test/invalid-address")
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "invalid_address"
    assert body["error"]["message"] == "bad addr"


async def test_not_found_maps_to_404(app, client):
    _attach_throwers(app)
    resp = await client.get("/_test/not-found")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_not_configured_maps_to_503(app, client):
    _attach_throwers(app)
    resp = await client.get("/_test/not-configured")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "not_configured"


async def test_aegis_default_uses_subclass_attrs(app, client):
    _attach_throwers(app)
    resp = await client.get("/_test/aegis-default")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
