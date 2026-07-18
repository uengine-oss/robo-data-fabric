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


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _strict_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return normalized == "true"


@dataclass(frozen=True)
class FabricSettings:
    host: str = os.getenv("DATA_FABRIC_HOST", "0.0.0.0")
    port: int = _bounded_int("DATA_FABRIC_PORT", 8404, 1, 65535)
    cors_origins: tuple[str, ...] = _origins()
    query_timeout_seconds: float = _bounded_float(
        "DATA_FABRIC_QUERY_TIMEOUT_SECONDS", 30.0, 0.1, 300.0
    )
    allow_neo4j_header_override: bool = _strict_bool(
        "DATA_FABRIC_ALLOW_NEO4J_HEADER_OVERRIDE", False
    )
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "neo4j")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")
    mindsdb_url: str | None = os.getenv("MINDSDB_URL") or None
    mindsdb_host: str = os.getenv("MINDSDB_HOST", "127.0.0.1")
    mindsdb_port: int = _bounded_int("MINDSDB_API_PORT", 47334, 1, 65535)
    mindsdb_replace_localhost: str = os.getenv(
        "MINDSDB_REPLACE_LOCALHOST", "host.docker.internal"
    )

    def __post_init__(self) -> None:
        if self.neo4j_database.lower() == "system":
            raise ValueError("NEO4J_DATABASE cannot be system")


settings = FabricSettings()
