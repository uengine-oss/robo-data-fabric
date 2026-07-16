import asyncio
import unittest
from unittest.mock import patch

import httpx

from app.connections.mindsdb_gateway import MindsDBService, _quote_identifier, _safe_connector_name


class _RecordingMindsDB(MindsDBService):
    def __init__(self) -> None:
        super().__init__("http://unused")
        self.queries: list[str] = []

    async def execute_query(self, query: str):
        self.queries.append(query)
        return {"type": "table", "columns": [], "data": [], "row_count": 0, "error": None}


def test_identifiers_are_validated_or_escaped_at_the_right_boundary() -> None:
    assert _safe_connector_name("orders-prod") == "orders-prod"
    assert _quote_identifier("order`items", "table name") == "`order``items`"
    try:
        _safe_connector_name("orders; DROP DATABASE prod")
    except ValueError:
        pass
    else:
        raise AssertionError("connector names must reject SQL fragments")


async def test_table_schema_query_escapes_real_database_identifiers() -> None:
    service = _RecordingMindsDB()
    await service.get_table_schema("sales-db", "order`items")
    assert service.queries == ["DESCRIBE `sales-db`.`order``items`"]


async def test_connection_inspection_executes_target_native_query() -> None:
    service = _RecordingMindsDB()
    result = await service.inspect_database("sales-db")
    assert result["success"] is False
    assert service.queries == [
        "SELECT * FROM `sales-db` (SELECT 1 AS robo_connection_probe)"
    ]


class _TimeoutClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, *args, **kwargs):
        raise httpx.ReadTimeout("controlled timeout")


async def test_query_timeout_is_returned_as_explicit_error() -> None:
    service = MindsDBService("http://timeout.test", timeout=0.1)
    with patch("app.connections.mindsdb_gateway.httpx.AsyncClient", return_value=_TimeoutClient()):
        result = await service.execute_query("SELECT 1")
    assert result["type"] == "error"
    assert "timeout" in result["error"].lower()
    assert result["execution_time"] >= 0


class MindsDBGatewayTest(unittest.IsolatedAsyncioTestCase):
    def test_identifier_boundary(self) -> None:
        test_identifiers_are_validated_or_escaped_at_the_right_boundary()

    async def test_real_identifiers_are_escaped(self) -> None:
        await test_table_schema_query_escapes_real_database_identifiers()

    async def test_inspection_uses_target_database(self) -> None:
        await test_connection_inspection_executes_target_native_query()

    async def test_timeout_is_not_reported_as_success(self) -> None:
        await test_query_timeout_is_returned_as_explicit_error()


if __name__ == "__main__":
    test_identifiers_are_validated_or_escaped_at_the_right_boundary()
    asyncio.run(test_table_schema_query_escapes_real_database_identifiers())
    print("[OK] MindsDB query boundaries")
