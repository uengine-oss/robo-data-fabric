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


def _bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
    value = float(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("DATA_FABRIC_HOST", "0.0.0.0")
    port: int = int(os.getenv("DATA_FABRIC_PORT", "8404"))
    cors_origins: tuple[str, ...] = _origins()
    query_timeout_seconds: float = _bounded_float(
        "DATA_FABRIC_QUERY_TIMEOUT_SECONDS", 30.0, 0.1, 300.0
    )
    allow_neo4j_header_override: bool = (
        os.getenv("DATA_FABRIC_ALLOW_NEO4J_HEADER_OVERRIDE", "false").lower() == "true"
    )


settings = Settings()
