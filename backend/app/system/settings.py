"""Data Fabric process configuration single source of truth."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _origins() -> tuple[str, ...]:
    raw = os.getenv(
        "DATA_FABRIC_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3003,http://127.0.0.1:3003",
    )
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("DATA_FABRIC_HOST", "0.0.0.0")
    port: int = int(os.getenv("DATA_FABRIC_PORT", "8404"))
    cors_origins: tuple[str, ...] = _origins()


settings = Settings()
