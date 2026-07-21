"""Per-request Neo4j override boundary."""
from fastapi import HTTPException, Request

from registry.connection import Neo4jOverride, set_override
from shared.config.settings import settings


async def apply_neo4j_override(request: Request) -> None:
    try:
        override = Neo4jOverride.from_headers(request.headers)
    except ValueError as error:
        raise HTTPException(400, "Invalid Neo4j override headers") from error
    if override is not None and not settings.allow_neo4j_header_override:
        raise HTTPException(403, "Neo4j header override is disabled")
    set_override(override)
