"""MindsDB HTTP transport and composed public gateway."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from mindsdb import admin, tables
from shared.config.settings import settings


logger = logging.getLogger(__name__)


def _result(
    result_type: str,
    *,
    columns: list[str] | None = None,
    data: list[list[Any]] | None = None,
    error: str | None = None,
    execution_time: float = 0.0,
) -> dict[str, Any]:
    rows = data or []
    return {
        "type": result_type,
        "columns": columns or [],
        "data": rows,
        "row_count": len(rows),
        "error": error,
        "execution_time": execution_time,
    }


class MindsDBTransport:
    """Low-level HTTP boundary; it does not own connector or table policy."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self._base_url = base_url
        self.timeout = settings.query_timeout_seconds if timeout is None else timeout

    @property
    def base_url(self) -> str:
        if self._base_url:
            return self._base_url.rstrip("/")
        if settings.mindsdb_url:
            return settings.mindsdb_url.rstrip("/")
        return f"http://{settings.mindsdb_host}:{settings.mindsdb_port}"

    async def execute_query(self, query: str) -> dict[str, Any]:
        """Execute one SQL request and normalize the MindsDB wire response."""
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/sql/query",
                    headers={"Content-Type": "application/json"},
                    json={"query": query},
                )
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("MindsDB response must be an object")
            elapsed = time.monotonic() - started
            if payload.get("type") == "error":
                logger.error("MindsDB rejected SQL request")
                return _result(
                    "error",
                    error="MindsDB query failed",
                    execution_time=elapsed,
                )
            if payload.get("type") == "table":
                data = payload.get("data", [])
                columns = payload.get("column_names", [])
                if not isinstance(data, list) or not isinstance(columns, list):
                    raise ValueError("MindsDB table response has invalid fields")
                return _result(
                    "table",
                    columns=columns,
                    data=data,
                    execution_time=elapsed,
                )
            return _result("ok", execution_time=elapsed)
        except httpx.TimeoutException:
            logger.warning("MindsDB SQL request timed out")
            return _result(
                "error",
                error="Query timeout - operation may still be running",
                execution_time=time.monotonic() - started,
            )
        except (httpx.HTTPError, ValueError):
            logger.exception("MindsDB SQL transport failed")
            return _result(
                "error",
                error="MindsDB request failed",
                execution_time=time.monotonic() - started,
            )

    async def create_database_request(
        self, payload: dict[str, Any], *, connector_name: str
    ) -> dict[str, Any]:
        """Send the connector-creation wire request without interpreting policy."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/databases/",
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
            if response.status_code in {200, 201}:
                return _result("ok")
            logger.warning(
                "MindsDB connector creation rejected",
                extra={"connector": connector_name, "status_code": response.status_code},
            )
            return _result("error", error="MindsDB connector creation failed")
        except httpx.TimeoutException:
            logger.warning(
                "MindsDB connector creation timed out",
                extra={"connector": connector_name},
            )
            return _result("error", error="MindsDB connector creation timed out")
        except httpx.HTTPError:
            logger.exception(
                "MindsDB connector transport failed",
                extra={"connector": connector_name},
            )
            return _result("error", error="MindsDB connector request failed")


class MindsDBGateway:
    """Composes transport with connector administration and table browsing."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        *,
        transport: MindsDBTransport | None = None,
    ) -> None:
        self._transport = transport or MindsDBTransport(base_url, timeout)

    async def execute_query(self, query: str) -> dict[str, Any]:
        return await self._transport.execute_query(query)

    async def create_database_request(
        self, payload: dict[str, Any], *, connector_name: str
    ) -> dict[str, Any]:
        return await self._transport.create_database_request(
            payload, connector_name=connector_name
        )

    async def check_connection(self) -> tuple[bool, str | None, str | None]:
        return await admin.check_connection(self)

    async def create_database(
        self, name: str, engine: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        return await admin.create_database(self, name, engine, parameters)

    async def drop_database(self, name: str) -> dict[str, Any]:
        return await admin.drop_database(self, name)

    async def inspect_database(self, name: str) -> dict[str, Any]:
        return await admin.inspect_database(self, name)

    async def get_tables(self, database: str) -> list[str]:
        return await tables.list_tables(self, database)

    async def get_table_schema(
        self, database: str, table: str
    ) -> list[dict[str, Any]]:
        return await tables.table_schema(self, database, table)

    async def sample_data(
        self, database: str, table: str, limit: int = 10
    ) -> dict[str, Any]:
        return await tables.sample_rows(self, database, table, limit)


mindsdb_gateway = MindsDBGateway()
