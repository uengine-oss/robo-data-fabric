"""Neo4j-backed DataSource registry.

이 registry는 연결의 비밀정보를 소유하지 않는다. Credential은 요청에서 MindsDB 등록으로만
전달되며 이 모듈의 query parameter, Neo4j property, 반환값에 들어오지 않는다.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from neo4j import AsyncGraphDatabase

from .neo4j_context import get_override


logger = logging.getLogger(__name__)
DATA_FABRIC_GRAPH_OWNER = "data-fabric"
DEFAULT_WORKSPACE_ID = "default"


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str = "neo4j"


class Neo4jService:
    """비밀정보 없는 DataSource 연결 registry."""

    def __init__(self, config: Neo4jConfig | None = None):
        self.config = config or Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "neo4j"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
        )
        self._drivers: dict[tuple[str, str, str], Any] = {}

    def _resolve_config(self) -> Neo4jConfig:
        override = get_override()
        if override is None:
            return self.config
        return Neo4jConfig(
            uri=override.uri,
            user=override.user,
            password=override.password,
            database=override.database or self.config.database,
        )

    async def _get_driver(self, config: Neo4jConfig):
        key = (config.uri, config.user, config.password)
        driver = self._drivers.get(key)
        if driver is None:
            driver = AsyncGraphDatabase.driver(config.uri, auth=(config.user, config.password))
            self._drivers[key] = driver
        return driver

    async def close(self) -> None:
        for driver in self._drivers.values():
            await driver.close()
        self._drivers.clear()

    async def execute_query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        config = self._resolve_config()
        driver = await self._get_driver(config)
        async with driver.session(database=config.database) as session:
            result = await session.run(query, params or {})
            return await result.data()

    async def create_datasource(
        self,
        name: str,
        engine: str,
        parameters: dict[str, Any],
        display_name: str | None = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> Optional[dict[str, Any]]:
        """안전한 연결 식별 정보만 저장한다. parameters는 allowlist로 축소한다."""
        query = """
        CREATE (ds:DataSource {
            datasource_id: randomUUID(),
            graph_owner: 'data-fabric',
            workspace_id: $workspace_id,
            name: $name,
            engine: $engine,
            display_name: $display_name,
            host: $host,
            port: $port,
            database: $database,
            user: $user,
            created_at: datetime(),
            updated_at: datetime()
        })
        RETURN ds {
            .datasource_id, .graph_owner, .workspace_id,
            .name, .engine, .display_name, .host, .port, .database, .user,
            created_at: toString(ds.created_at)
        } AS datasource
        """
        safe_params = {
            "name": name,
            "engine": engine,
            "display_name": display_name or name,
            "workspace_id": workspace_id or DEFAULT_WORKSPACE_ID,
            "host": parameters.get("host", ""),
            "port": parameters.get("port", 0),
            "database": parameters.get("database", ""),
            "user": parameters.get("user", parameters.get("username", "")),
        }
        result = await self.execute_query(query, safe_params)
        return result[0]["datasource"] if result else None

    async def get_datasources(self) -> list[dict[str, Any]]:
        query = """
        MATCH (ds:DataSource {graph_owner: 'data-fabric'})
        RETURN ds {
            .datasource_id, .graph_owner, .workspace_id,
            .name, .engine, .display_name, .host, .port, .database, .user,
            created_at: toString(ds.created_at)
        } AS datasource
        ORDER BY ds.name
        """
        return [row["datasource"] for row in await self.execute_query(query)]

    async def get_datasource(self, name: str) -> Optional[dict[str, Any]]:
        query = """
        MATCH (ds:DataSource {name: $name, graph_owner: 'data-fabric'})
        RETURN ds {
            .datasource_id, .graph_owner, .workspace_id,
            .name, .engine, .display_name, .host, .port, .database, .user,
            created_at: toString(ds.created_at)
        } AS datasource
        """
        result = await self.execute_query(query, {"name": name})
        return result[0]["datasource"] if result else None

    async def delete_datasource(self, name: str) -> bool:
        """Registry와 이 DataSource에서만 도달하는 과거 extraction subtree를 제거한다."""
        query = """
        MATCH (ds:DataSource {name: $name, graph_owner: 'data-fabric'})
        OPTIONAL MATCH (ds)-[:HAS_SCHEMA]->(s:Schema)
        OPTIONAL MATCH (s)-[:HAS_TABLE]->(t:Table)
        OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
        WITH ds, collect(DISTINCT c) AS columns,
             collect(DISTINCT t) AS tables, collect(DISTINCT s) AS schemas
        FOREACH (node IN columns | DETACH DELETE node)
        FOREACH (node IN tables | DETACH DELETE node)
        FOREACH (node IN schemas | DETACH DELETE node)
        DETACH DELETE ds
        RETURN 1 AS deleted
        """
        result = await self.execute_query(query, {"name": name})
        return bool(result and result[0]["deleted"] == 1)

    async def ensure_constraints(self) -> None:
        """실패를 숨기지 않고 registry identity 제약을 보장한다."""
        constraints = (
            "CREATE CONSTRAINT datasource_name IF NOT EXISTS "
            "FOR (ds:DataSource) REQUIRE ds.name IS UNIQUE",
            "CREATE CONSTRAINT datasource_id IF NOT EXISTS "
            "FOR (ds:DataSource) REQUIRE ds.datasource_id IS UNIQUE",
        )
        for query in constraints:
            await self.execute_query(query)


datasource_registry = Neo4jService()
