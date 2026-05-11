"""Domain exceptions."""
from __future__ import annotations


class AegisError(Exception):
    code: str = "internal_error"
    status_code: int = 500


class NotFoundError(AegisError):
    code = "not_found"
    status_code = 404


class ConfigError(AegisError):
    code = "not_configured"
    status_code = 503
