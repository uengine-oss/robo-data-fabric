"""MindsDB table browsing and bounded sample policy."""
from __future__ import annotations

import re

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


# MindsDB 가 `SHOW COLUMNS` 의 타입을 못 채우고 **information_schema 의 열 이름을
# 그대로** 돌려주는 경우가 있다 — 숫자형이 `decimal(4,NUMERIC_SCALE)` 로 온다
# (2026-10-26 실측: mindsdb 에 직접 물어도 같다 · ISS-64). v26.1.0 이 2026-04-23
# 판이고 그 뒤로 새 판이 없어 기다릴 수 없다.
#
# **채워지지 않은 자리만** 지운다 — 없는 값을 지어내지 않고, 아는 것만 남긴다.
#   decimal(4,NUMERIC_SCALE)                  -> decimal(4)
#   decimal(NUMERIC_PRECISION,NUMERIC_SCALE)  -> decimal
#   varchar(10)                               -> 그대로
_UNRESOLVED_TYPE_ARG = re.compile(
    r"^(?:NUMERIC_SCALE|NUMERIC_PRECISION|CHARACTER_MAXIMUM_LENGTH|DATETIME_PRECISION)$"
)


def _clean_column_type(raw: Any) -> str:
    text = str(raw or "").strip()
    if "(" not in text or ")" not in text:
        return text
    head, _, rest = text.partition("(")
    args = [a.strip() for a in rest.rstrip(")").split(",")]
    kept = [a for a in args if not _UNRESOLVED_TYPE_ARG.match(a)]
    if len(kept) == len(args):
        return text
    head = head.strip()
    return f"{head}({','.join(kept)})" if kept else head


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
            "type": _clean_column_type(row[1]) if len(row) > 1 else "unknown",
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
