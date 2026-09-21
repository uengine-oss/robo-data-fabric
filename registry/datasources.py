"""Neo4j-backed DataSource registry.

이 registry는 연결의 비밀정보를 소유하지 않는다. Credential은 요청에서 MindsDB 등록으로만
전달되며 이 모듈의 query parameter, Neo4j property, 반환값에 들어오지 않는다.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from neo4j import AsyncGraphDatabase

from .connection import get_override
from .driver import Neo4jConfig
from .scope import DATA_FABRIC_GRAPH_OWNER
from shared.config.settings import settings


logger = logging.getLogger(__name__)


class DatasourceRegistry:
    """비밀정보 없는 DataSource 연결 registry."""

    def __init__(self, config: Neo4jConfig | None = None):
        self.config = config or Neo4jConfig(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
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
    ) -> Optional[dict[str, Any]]:
        """안전한 연결 식별 정보만 저장한다. parameters는 allowlist로 축소한다."""
        query = """
        CREATE (ds:DataSource {
            _owner: $owner,
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
            .name, .engine, .display_name, .host, .port, .database, .user,
            created_at: toString(ds.created_at)
        } AS datasource
        """
        safe_params = {
            "name": name,
            "owner": DATA_FABRIC_GRAPH_OWNER,
            "engine": engine,
            "display_name": display_name or name,
            "host": parameters.get("host", ""),
            "port": parameters.get("port", 0),
            "database": parameters.get("database", ""),
            "user": parameters.get("user", parameters.get("username", "")),
        }
        result = await self.execute_query(query, safe_params)
        return result[0]["datasource"] if result else None

    async def get_datasources(self) -> list[dict[str, Any]]:
        query = """
        MATCH (ds:DataSource {_owner: $owner})
        RETURN ds {
            .name, .engine, .display_name, .host, .port, .database, .user,
            created_at: toString(ds.created_at)
        } AS datasource
        ORDER BY ds.name
        """
        return [
            row["datasource"]
            for row in await self.execute_query(
                query, {"owner": DATA_FABRIC_GRAPH_OWNER}
            )
        ]

    async def get_datasource(self, name: str) -> Optional[dict[str, Any]]:
        query = """
        MATCH (ds:DataSource {name: $name, _owner: $owner})
        RETURN ds {
            .name, .engine, .display_name, .host, .port, .database, .user,
            created_at: toString(ds.created_at)
        } AS datasource
        """
        result = await self.execute_query(
            query, {"name": name, "owner": DATA_FABRIC_GRAPH_OWNER}
        )
        return result[0]["datasource"] if result else None

    async def delete_datasource(self, name: str) -> bool:
        """Remove only the Data Fabric-owned registry node.

        Data Fabric no longer owns extracted schema/table nodes. Traversing and
        deleting a legacy subtree here could destroy nodes shared with Analyzer
        or Architect, so metadata cleanup belongs to its owning service.
        """
        query = """
        MATCH (ds:DataSource {name: $name, _owner: $owner})
        DETACH DELETE ds
        RETURN 1 AS deleted
        """
        result = await self.execute_query(
            query, {"name": name, "owner": DATA_FABRIC_GRAPH_OWNER}
        )
        return bool(result and result[0]["deleted"] == 1)

    async def ensure_constraints(self) -> None:
        """실패를 숨기지 않고 registry identity 제약을 보장한다."""
        constraints = (
            "CREATE CONSTRAINT data_fabric_datasource_identity IF NOT EXISTS "
            "FOR (ds:DataSource) REQUIRE (ds._owner, ds.name) IS UNIQUE",
        )
        for query in constraints:
            await self.execute_query(query)


datasource_registry = DatasourceRegistry()
