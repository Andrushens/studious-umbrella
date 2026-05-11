"""Exception → JSON handler registration."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aegis.clients.alchemy import AlchemyError
from aegis.clients.etherscan import EtherscanError, RateLimitedError
from aegis.errors import AegisError, ConfigError, NotFoundError
from aegis.eth import InvalidAddressError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidAddressError)
    async def _invalid_address(_: Request, exc: InvalidAddressError):
        return _err(422, "invalid_address", str(exc))

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError):
        return _err(404, "not_found", str(exc))

    @app.exception_handler(ConfigError)
    async def _not_configured(_: Request, exc: ConfigError):
        return _err(503, "not_configured", str(exc))

    @app.exception_handler(RateLimitedError)
    async def _rate_limited(_: Request, exc: RateLimitedError):
        return _err(503, "upstream_rate_limited", str(exc))

    @app.exception_handler(EtherscanError)
    async def _etherscan(_: Request, exc: EtherscanError):
        return _err(502, "upstream_etherscan", str(exc))

    @app.exception_handler(AlchemyError)
    async def _alchemy(_: Request, exc: AlchemyError):
        return _err(502, "upstream_alchemy", str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        # Pydantic v2 error dicts may contain non-serializable objects in
        # the `ctx` field (e.g. the original ValueError). Strip those keys.
        safe_errors = [
            {k: v for k, v in err.items() if k not in ("ctx", "url")}
            for err in exc.errors()
        ]
        return _err(
            422,
            "validation_error",
            "Request validation failed",
            details={"errors": safe_errors},
        )

    @app.exception_handler(AegisError)
    async def _aegis_default(_: Request, exc: AegisError):
        return _err(exc.status_code, exc.code, str(exc) or exc.code)


def _err(
    status: int, code: str, message: str, details: dict | None = None
) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)
