"""Sentry initialization (opt-in via SENTRY_DSN env)."""
from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from aegis.config import Settings


def init_sentry(settings: Settings) -> None:
    dsn = settings.sentry_dsn.strip()
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.env,
        traces_sample_rate=0.0,
        send_default_pii=False,
        integrations=[
            FastApiIntegration(),
            AsyncioIntegration(),
            SqlalchemyIntegration(),
        ],
    )
