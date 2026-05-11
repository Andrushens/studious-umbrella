"""FastAPI app factory + lifespan."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from aegis.api import devices, healthz
from aegis.api.errors import register_exception_handlers
from aegis.clients.alchemy import AlchemyClient
from aegis.clients.base import build_http_client
from aegis.clients.etherscan import EtherscanClient
from aegis.config import Settings, get_settings
from aegis.db import build_engine, build_sessionmaker, init_db
from aegis.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    app = FastAPI(title="Aegis Backend", version="0.1.0", lifespan=_lifespan)
    app.state.settings = settings
    register_exception_handlers(app)
    _register_request_id(app)
    app.include_router(healthz.router, prefix="/v1")
    app.include_router(devices.router, prefix="/v1")
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings: Settings = app.state.settings

    engine = build_engine(settings.database_url)
    await init_db(engine)
    sessionmaker = build_sessionmaker(engine)

    http = build_http_client(timeout=settings.http_timeout_seconds)
    etherscan = EtherscanClient(http, settings.etherscan_api_key, settings.etherscan_base_url)
    alchemy = AlchemyClient(http, settings.alchemy_api_key, settings.alchemy_base_url_tmpl)

    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.http = http
    app.state.etherscan = etherscan
    app.state.alchemy = alchemy

    from aegis.scheduler import build_scheduler

    scheduler = None
    if settings.scheduler_enabled:
        scheduler = build_scheduler(settings, sessionmaker, etherscan, alchemy)
        scheduler.start()
    app.state.scheduler = scheduler

    structlog.get_logger("aegis").info("startup_complete", env=settings.env)
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        await http.aclose()
        await engine.dispose()


def _register_request_id(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = request_id
        return response


app = create_app()
