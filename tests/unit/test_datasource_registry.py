import asyncio
import unittest

from registry.datasources import DatasourceRegistry
from registry.driver import Neo4jConfig


class _RecordingRegistry(DatasourceRegistry):
    def __init__(self) -> None:
        super().__init__(Neo4jConfig("bolt://unused", "neo4j", "unused"))
        self.calls: list[tuple[str, dict]] = []

    async def execute_query(self, query: str, params: dict | None = None):
        self.calls.append((query, params or {}))
        if "RETURN ds" in query:
            return [{"datasource": {"datasource_id": "ds-1", "name": "orders"}}]
        return [{"deleted": 1}]


async def test_registry_never_persists_or_returns_credentials() -> None:
    registry = _RecordingRegistry()
    result = await registry.create_datasource(
        "orders", "postgres",
        {"host": "db", "port": 5432, "database": "orders", "user": "app", "password": "secret"},
        workspace_id="workspace-a",
    )
    query, params = registry.calls[0]
    assert result["datasource_id"] == "ds-1"
    assert "password" not in query.lower() and "api_key" not in query.lower()
    assert "password" not in params and "api_key" not in params
    assert "datasource_id" in query
    assert "graph_owner" in query and params["graph_owner"] == "data-fabric"
    assert params["registry_key"] == "data-fabric:orders"
    assert "workspace_id" in query


async def test_delete_only_removes_the_owned_registry_node() -> None:
    registry = _RecordingRegistry()
    assert await registry.delete_datasource("orders") is True
    query, _ = registry.calls[0]
    assert "(ds:DataSource" in query
    assert "HAS_SCHEMA" not in query and "HAS_TABLE" not in query and "HAS_COLUMN" not in query
    assert "MATCH (n)" not in query
    assert registry.calls[0][1]["graph_owner"] == "data-fabric"


async def test_constraints_replace_cross_owner_name_uniqueness() -> None:
    registry = _RecordingRegistry()
    await registry.ensure_constraints()
    queries = [query for query, _ in registry.calls]
    assert queries[0] == "DROP CONSTRAINT datasource_name IF EXISTS"
    assert any("registry_key" in query for query in queries)
    assert not any("REQUIRE ds.name IS UNIQUE" in query for query in queries)


class DataSourceRegistryTest(unittest.IsolatedAsyncioTestCase):
    async def test_credentials_are_never_persisted_or_returned(self) -> None:
        await test_registry_never_persists_or_returns_credentials()

    async def test_delete_is_registry_subtree_scoped(self) -> None:
        await test_delete_only_removes_the_owned_registry_node()

    async def test_constraints_are_owner_isolated(self) -> None:
        await test_constraints_replace_cross_owner_name_uniqueness()


if __name__ == "__main__":
    asyncio.run(test_registry_never_persists_or_returns_credentials())
    asyncio.run(test_delete_only_removes_the_owned_registry_node())
    print("[OK] datasource registry contract")
