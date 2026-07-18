"""MindsDB table browsing and bounded sample policy."""
from __future__ import annotations

from typing import Any, Protocol

from mindsdb.quoting import quote_identifier


class QueryTransport(Protocol):
    async def execute_query(self, query: str) -> dict[str, Any]: ...


async def list_tables(
    transport: QueryTransport, database: str
) -> list[str]:
    quoted_database = quote_identifier(database, "database name")
    result = await transport.execute_query(f"SHOW TABLES FROM {quoted_database}")
    if result["type"] == "error":
        raise RuntimeError("MindsDB table listing failed")
    if result["type"] != "table":
        raise RuntimeError("MindsDB table listing returned no table result")
    return [str(row[0]) for row in result["data"] if row]


async def table_schema(
    transport: QueryTransport, database: str, table: str
) -> list[dict[str, Any]]:
    quoted_database = quote_identifier(database, "database name")
    quoted_table = quote_identifier(table, "table name")
    result = await transport.execute_query(
        f"SHOW COLUMNS FROM {quoted_database}.{quoted_table}"
    )
    if result["type"] == "error":
        raise RuntimeError("MindsDB schema lookup failed")
    if result["type"] != "table":
        raise RuntimeError("MindsDB schema lookup returned no table result")
    return [
        {
            "name": row[0] if row else "",
            "type": row[1] if len(row) > 1 else "unknown",
            "nullable": row[2] if len(row) > 2 else None,
            "key": row[3] if len(row) > 3 else None,
        }
        for row in result["data"]
    ]


async def sample_rows(
    transport: QueryTransport, database: str, table: str, limit: int
) -> dict[str, Any]:
    quoted_database = quote_identifier(database, "database name")
    quoted_table = quote_identifier(table, "table name")
    if not 1 <= limit <= 1000:
        raise ValueError("sample limit must be between 1 and 1000")
    return await transport.execute_query(
        f"SELECT * FROM {quoted_database}.{quoted_table} LIMIT {limit}"
    )
