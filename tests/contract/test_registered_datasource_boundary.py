import unittest

from fastapi import HTTPException

import api.query as query_api
import api.tables as table_api
from contracts.query import QueryRequest


class _Registry:
    def __init__(self, exists: bool):
        self.exists = exists

    async def get_datasource(self, name):
        return {"name": name} if self.exists else None


class _Gateway:
    def __init__(self):
        self.calls = []

    async def execute_query(self, query):
        self.calls.append(("query", query))
        return {
            "type": "table",
            "columns": ["value"],
            "data": [[1]],
            "row_count": 1,
            "error": None,
            "execution_time": 0.01,
        }

    async def get_tables(self, name):
        self.calls.append(("tables", name))
        return ["orders"]


class RegisteredDatasourceBoundaryTest(unittest.IsolatedAsyncioTestCase):
    async def test_unregistered_query_never_reaches_mindsdb(self):
        gateway = _Gateway()
        originals = query_api.datasource_registry, query_api.mindsdb_gateway
        query_api.datasource_registry, query_api.mindsdb_gateway = _Registry(False), gateway
        try:
            with self.assertRaises(HTTPException) as raised:
                await query_api.execute_query(
                    QueryRequest(datasource="unknown", query="SELECT 1", max_rows=1)
                )
        finally:
            query_api.datasource_registry, query_api.mindsdb_gateway = originals
        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(gateway.calls, [])

    async def test_unregistered_table_browse_never_reaches_mindsdb(self):
        gateway = _Gateway()
        originals = table_api.datasource_registry, table_api.mindsdb_gateway
        table_api.datasource_registry, table_api.mindsdb_gateway = _Registry(False), gateway
        try:
            with self.assertRaises(HTTPException) as raised:
                await table_api.get_tables("unknown")
        finally:
            table_api.datasource_registry, table_api.mindsdb_gateway = originals
        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(gateway.calls, [])

    async def test_registered_query_is_read_bounded_before_gateway(self):
        gateway = _Gateway()
        originals = query_api.datasource_registry, query_api.mindsdb_gateway
        query_api.datasource_registry, query_api.mindsdb_gateway = _Registry(True), gateway
        try:
            response = await query_api.execute_query(
                QueryRequest(datasource="shop-mall", query="SELECT 1", max_rows=7)
            )
        finally:
            query_api.datasource_registry, query_api.mindsdb_gateway = originals
        self.assertEqual(response.row_count, 1)
        self.assertIn("`shop-mall`", gateway.calls[0][1])
        self.assertIn("LIMIT 7", gateway.calls[0][1])


if __name__ == "__main__":
    unittest.main()
