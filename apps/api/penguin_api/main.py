"""FastAPI service skeleton for future dashboard integration."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("API service initialized.")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="DiscordPenguinBot API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {
            "service": "api",
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return app


app = create_app()
