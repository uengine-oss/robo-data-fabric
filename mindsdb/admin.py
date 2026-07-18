"""MindsDB connector administration policy."""
from __future__ import annotations

from typing import Any, Protocol

from mindsdb.quoting import quote_identifier, safe_connector_name, safe_engine_name


class AdminTransport(Protocol):
    async def execute_query(self, query: str) -> dict[str, Any]: ...

    async def create_database_request(
        self, payload: dict[str, Any], *, connector_name: str
    ) -> dict[str, Any]: ...


async def check_connection(
    transport: AdminTransport,
) -> tuple[bool, str | None, str | None]:
    result = await transport.execute_query("SELECT VERSION()")
    if result["type"] == "error":
        return False, None, result["error"]
    version = result["data"][0][0] if result["data"] else "Unknown"
    return True, str(version), None


async def create_database(
    transport: AdminTransport,
    name: str,
    engine: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    connector_name = safe_connector_name(name)
    engine_name = safe_engine_name(engine)
    payload = {
        "database": {
            "name": connector_name,
            "engine": engine_name,
            "parameters": parameters,
        }
    }
    return await transport.create_database_request(
        payload, connector_name=connector_name
    )


async def drop_database(
    transport: AdminTransport, name: str
) -> dict[str, Any]:
    connector_name = safe_connector_name(name)
    quoted = quote_identifier(connector_name, "database name")
    return await transport.execute_query(f"DROP DATABASE IF EXISTS {quoted}")


async def inspect_database(
    transport: AdminTransport, name: str
) -> dict[str, Any]:
    connector_name = safe_connector_name(name)
    quoted = quote_identifier(connector_name, "database name")
    result = await transport.execute_query(
        f"SELECT * FROM {quoted} (SELECT 1 AS robo_connection_probe)"
    )
    return {
        "success": result["type"] == "table" and result["data"] == [[1]],
        "table_count": 0,
    }
