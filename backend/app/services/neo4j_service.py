"""Neo4j Service - DataSource Node Management"""
import os
from typing import Optional, Dict, Any, List
from neo4j import AsyncGraphDatabase
from dataclasses import dataclass


@dataclass
class Neo4jConfig:
    """Neo4j 연결 설정"""
    uri: str
    user: str
    password: str
    database: str = "neo4j"


class Neo4jService:
    """Neo4j를 사용한 DataSource 관리 서비스"""
    
    def __init__(self, config: Neo4jConfig = None):
        if config is None:
            config = Neo4jConfig(
                uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                user=os.getenv("NEO4J_USER", "neo4j"),
                password=os.getenv("NEO4J_PASSWORD", "neo4j"),
                database=os.getenv("NEO4J_DATABASE", "neo4j")
            )
        self.config = config
        self._driver = None
    
    async def _get_driver(self):
        """드라이버 lazy 초기화"""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password)
            )
        return self._driver
    
    async def close(self):
        """드라이버 종료"""
        if self._driver:
            await self._driver.close()
            self._driver = None
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Cypher 쿼리 실행"""
        driver = await self._get_driver()
        async with driver.session(database=self.config.database) as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records
    
    # ========================================
    # DataSource CRUD Operations
    # ========================================
    
    async def create_datasource(
        self,
        name: str,
        engine: str,
        parameters: Dict[str, Any],
        display_name: str = None
    ) -> Dict[str, Any]:
        """DataSource 노드 생성 - 연결 정보(비밀번호 포함) 모두 저장"""
        # TODO: 프로덕션에서는 비밀번호를 암호화하여 저장해야 함
        query = """
        MERGE (ds:DataSource {name: $name})
        SET ds.engine = $engine,
            ds.display_name = $display_name,
            ds.host = $host,
            ds.port = $port,
            ds.database = $database,
            ds.user = $user,
            ds.password = $password,
            ds.created_at = datetime(),
            ds.updated_at = datetime()
        RETURN ds {
            .name, .engine, .display_name, .host, .port, .database, .user,
            created_at: toString(ds.created_at)
        } AS datasource
        """
        
        result = await self.execute_query(query, {
            "name": name,
            "engine": engine,
            "display_name": display_name or name,
            "host": parameters.get("host", ""),
            "port": parameters.get("port", 0),
            "database": parameters.get("database", ""),
            "user": parameters.get("user", ""),
            "password": parameters.get("password", "")
        })
        
        return result[0]["datasource"] if result else None
    
    async def get_datasources(self) -> List[Dict[str, Any]]:
        """모든 DataSource 노드 조회"""
        query = """
        MATCH (ds:DataSource)
        OPTIONAL MATCH (ds)-[:HAS_SCHEMA]->(s:Schema)
        WITH ds, COUNT(s) as schema_count
        RETURN ds {
            .name, .engine, .display_name, .host, .port, .database, .user,
            schema_count: schema_count,
            created_at: toString(ds.created_at)
        } AS datasource
        ORDER BY ds.name
        """
        results = await self.execute_query(query)
        return [r["datasource"] for r in results]
    
    async def get_datasource(self, name: str, include_password: bool = False) -> Optional[Dict[str, Any]]:
        """특정 DataSource 조회"""
        if include_password:
            query = """
            MATCH (ds:DataSource {name: $name})
            OPTIONAL MATCH (ds)-[:HAS_SCHEMA]->(s:Schema)
            WITH ds, COLLECT(s.name) as schemas
            RETURN ds {
                .name, .engine, .display_name, .host, .port, .database, .user, .password,
                schemas: schemas,
                created_at: toString(ds.created_at)
            } AS datasource
            """
        else:
            query = """
            MATCH (ds:DataSource {name: $name})
            OPTIONAL MATCH (ds)-[:HAS_SCHEMA]->(s:Schema)
            WITH ds, COLLECT(s.name) as schemas
            RETURN ds {
                .name, .engine, .display_name, .host, .port, .database, .user,
                schemas: schemas,
                created_at: toString(ds.created_at)
            } AS datasource
            """
        results = await self.execute_query(query, {"name": name})
        return results[0]["datasource"] if results else None
    
    async def get_connection_params(self, name: str) -> Optional[Dict[str, Any]]:
        """DataSource의 연결 파라미터 조회 (비밀번호 포함)"""
        query = """
        MATCH (ds:DataSource {name: $name})
        RETURN {
            engine: ds.engine,
            host: ds.host,
            port: ds.port,
            database: ds.database,
            user: ds.user,
            password: ds.password
        } AS connection
        """
        results = await self.execute_query(query, {"name": name})
        return results[0]["connection"] if results else None
    
    async def delete_datasource(self, name: str) -> bool:
        """DataSource 삭제 (연결된 Schema, Table, Column도 함께 삭제)"""
        query = """
        MATCH (ds:DataSource {name: $name})
        OPTIONAL MATCH (ds)-[:HAS_SCHEMA]->(s:Schema)
        OPTIONAL MATCH (s)-[:HAS_TABLE]->(t:Table)
        OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
        DETACH DELETE ds, s, t, c
        RETURN COUNT(*) as deleted
        """
        results = await self.execute_query(query, {"name": name})
        return results[0]["deleted"] > 0 if results else False
    
    async def update_datasource(
        self,
        name: str,
        engine: str = None,
        parameters: Dict[str, Any] = None,
        display_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """DataSource 업데이트 (비밀번호 포함)"""
        set_clauses = ["ds.updated_at = datetime()"]
        params = {"name": name}
        
        if engine:
            set_clauses.append("ds.engine = $engine")
            params["engine"] = engine
        if display_name:
            set_clauses.append("ds.display_name = $display_name")
            params["display_name"] = display_name
        if parameters:
            for key, value in parameters.items():
                # 비밀번호도 저장 (TODO: 프로덕션에서는 암호화 필요)
                set_clauses.append(f"ds.{key} = ${key}")
                params[key] = value
        
        query = f"""
        MATCH (ds:DataSource {{name: $name}})
        SET {', '.join(set_clauses)}
        RETURN ds {{
            .name, .engine, .display_name, .host, .port, .database, .user,
            updated_at: toString(ds.updated_at)
        }} AS datasource
        """
        results = await self.execute_query(query, params)
        return results[0]["datasource"] if results else None
    
    # ========================================
    # Schema Operations (DataSource -> Schema)
    # ========================================
    
    async def get_schemas(self, datasource_name: str) -> List[Dict[str, Any]]:
        """DataSource에 속한 Schema 목록 조회"""
        query = """
        MATCH (ds:DataSource {name: $datasource_name})-[:HAS_SCHEMA]->(s:Schema)
        OPTIONAL MATCH (s)-[:HAS_TABLE]->(t:Table)
        WITH s, COUNT(t) as table_count
        RETURN s {
            .name, .description,
            table_count: table_count
        } AS schema
        ORDER BY s.name
        """
        results = await self.execute_query(query, {"datasource_name": datasource_name})
        return [r["schema"] for r in results]
    
    async def create_schema(
        self,
        datasource_name: str,
        schema_name: str,
        description: str = None
    ) -> Dict[str, Any]:
        """Schema 노드 생성 및 DataSource에 연결"""
        query = """
        MATCH (ds:DataSource {name: $datasource_name})
        MERGE (s:Schema {name: $schema_name})
        SET s.description = $description,
            s.created_at = datetime()
        MERGE (ds)-[:HAS_SCHEMA]->(s)
        RETURN s {.name, .description} AS schema
        """
        results = await self.execute_query(query, {
            "datasource_name": datasource_name,
            "schema_name": schema_name,
            "description": description or ""
        })
        return results[0]["schema"] if results else None
    
    # ========================================
    # Table Operations (Schema -> Table)
    # ========================================
    
    async def get_tables(self, datasource_name: str, schema_name: str = None) -> List[Dict[str, Any]]:
        """DataSource/Schema에 속한 Table 목록 조회"""
        if schema_name:
            query = """
            MATCH (ds:DataSource {name: $datasource_name})-[:HAS_SCHEMA]->(s:Schema {name: $schema_name})-[:HAS_TABLE]->(t:Table)
            OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
            WITH t, COUNT(c) as column_count
            RETURN t {
                .name, .description, .schema,
                column_count: column_count
            } AS table
            ORDER BY t.name
            """
            params = {"datasource_name": datasource_name, "schema_name": schema_name}
        else:
            query = """
            MATCH (ds:DataSource {name: $datasource_name})-[:HAS_SCHEMA]->(s:Schema)-[:HAS_TABLE]->(t:Table)
            OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
            WITH t, s, COUNT(c) as column_count
            RETURN t {
                .name, .description,
                schema: s.name,
                column_count: column_count
            } AS table
            ORDER BY s.name, t.name
            """
            params = {"datasource_name": datasource_name}
        
        results = await self.execute_query(query, params)
        return [r["table"] for r in results]
    
    # ========================================
    # Constraint & Index Setup
    # ========================================
    
    async def ensure_constraints(self):
        """DataSource 관련 제약조건 생성"""
        constraints = [
            "CREATE CONSTRAINT datasource_name IF NOT EXISTS FOR (ds:DataSource) REQUIRE ds.name IS UNIQUE",
        ]
        
        for query in constraints:
            try:
                await self.execute_query(query)
            except Exception:
                pass  # 이미 존재할 수 있음


# Singleton 인스턴스
neo4j_service = Neo4jService()
