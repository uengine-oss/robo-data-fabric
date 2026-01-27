"""
Schema Introspection Service
OpenMetadata 스타일의 데이터 소스 메타데이터 추출 서비스

데이터베이스에 연결하여 테이블, 컬럼, 외래키 등의 메타데이터를 추출합니다.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# 데이터 모델
# ============================================================================

@dataclass
class ColumnMetadata:
    """컬럼 메타데이터"""
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default_value: Optional[str] = None
    description: Optional[str] = None
    ordinal_position: int = 0
    max_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None


@dataclass
class ForeignKeyMetadata:
    """외래키 메타데이터"""
    name: str
    source_schema: str
    source_table: str
    source_column: str
    target_schema: str
    target_table: str
    target_column: str


@dataclass
class TableMetadata:
    """테이블 메타데이터"""
    name: str
    schema: str
    table_type: str = "TABLE"  # TABLE, VIEW, MATERIALIZED_VIEW
    description: Optional[str] = None
    columns: List[ColumnMetadata] = field(default_factory=list)
    row_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SchemaMetadata:
    """스키마 메타데이터"""
    name: str
    description: Optional[str] = None
    tables: List[TableMetadata] = field(default_factory=list)


@dataclass
class DatabaseMetadata:
    """데이터베이스 메타데이터"""
    name: str
    engine: str
    host: Optional[str] = None
    port: Optional[int] = None
    schemas: List[SchemaMetadata] = field(default_factory=list)
    foreign_keys: List[ForeignKeyMetadata] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExtractionProgress:
    """추출 진행 상황"""
    phase: str
    message: str
    progress: int  # 0-100
    total_schemas: int = 0
    processed_schemas: int = 0
    total_tables: int = 0
    processed_tables: int = 0
    error: Optional[str] = None


# ============================================================================
# 데이터베이스 어댑터 기본 클래스
# ============================================================================

class DatabaseAdapter(ABC):
    """데이터베이스 어댑터 기본 클래스 (OpenMetadata 스타일)"""
    
    def __init__(self, connection_params: Dict[str, Any]):
        self.connection_params = connection_params
        self.connection = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """데이터베이스 연결"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """연결 해제"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> tuple[bool, Optional[str]]:
        """연결 테스트"""
        pass
    
    @abstractmethod
    async def get_schemas(self) -> List[str]:
        """스키마 목록 조회"""
        pass
    
    @abstractmethod
    async def get_tables(self, schema: str) -> List[TableMetadata]:
        """테이블 목록 조회"""
        pass
    
    @abstractmethod
    async def get_columns(self, schema: str, table: str) -> List[ColumnMetadata]:
        """컬럼 목록 조회"""
        pass
    
    @abstractmethod
    async def get_foreign_keys(self, schema: str = None) -> List[ForeignKeyMetadata]:
        """외래키 조회"""
        pass
    
    async def extract_metadata(
        self, 
        schemas: List[str] = None,
        include_columns: bool = True,
        include_foreign_keys: bool = True
    ) -> AsyncGenerator[tuple[ExtractionProgress, Optional[DatabaseMetadata]], None]:
        """
        메타데이터 추출 (스트리밍)
        진행 상황과 최종 결과를 yield
        """
        result = DatabaseMetadata(
            name=self.connection_params.get('database', 'unknown'),
            engine=self.__class__.__name__.replace('Adapter', '').lower(),
            host=self.connection_params.get('host'),
            port=self.connection_params.get('port')
        )
        
        try:
            # 연결
            yield ExtractionProgress(
                phase="connecting",
                message="데이터베이스 연결 중...",
                progress=5
            ), None
            
            await self.connect()
            
            # 스키마 목록 조회
            yield ExtractionProgress(
                phase="schemas",
                message="스키마 목록 조회 중...",
                progress=10
            ), None
            
            all_schemas = await self.get_schemas()
            target_schemas = schemas if schemas else all_schemas
            total_schemas = len(target_schemas)
            
            yield ExtractionProgress(
                phase="schemas",
                message=f"{total_schemas}개 스키마 발견",
                progress=15,
                total_schemas=total_schemas
            ), None
            
            # 테이블 및 컬럼 추출
            all_tables_count = 0
            processed_tables = 0
            
            for idx, schema_name in enumerate(target_schemas):
                yield ExtractionProgress(
                    phase="tables",
                    message=f"스키마 '{schema_name}' 처리 중...",
                    progress=20 + int(60 * idx / total_schemas),
                    total_schemas=total_schemas,
                    processed_schemas=idx
                ), None
                
                try:
                    tables = await self.get_tables(schema_name)
                    schema_meta = SchemaMetadata(name=schema_name, tables=[])
                    
                    for table in tables:
                        all_tables_count += 1
                        
                        if include_columns:
                            try:
                                columns = await self.get_columns(schema_name, table.name)
                                table.columns = columns
                            except Exception as e:
                                logger.warning(f"컬럼 조회 실패: {schema_name}.{table.name}: {e}")
                        
                        schema_meta.tables.append(table)
                        processed_tables += 1
                        
                        if processed_tables % 10 == 0:
                            yield ExtractionProgress(
                                phase="tables",
                                message=f"테이블 처리 중: {processed_tables}/{all_tables_count}",
                                progress=20 + int(60 * (idx + 0.5) / total_schemas),
                                total_schemas=total_schemas,
                                processed_schemas=idx,
                                total_tables=all_tables_count,
                                processed_tables=processed_tables
                            ), None
                    
                    result.schemas.append(schema_meta)
                    
                except Exception as e:
                    logger.error(f"스키마 처리 실패: {schema_name}: {e}")
            
            # 외래키 추출
            if include_foreign_keys:
                yield ExtractionProgress(
                    phase="foreign_keys",
                    message="외래키 관계 추출 중...",
                    progress=85,
                    total_schemas=total_schemas,
                    processed_schemas=total_schemas,
                    total_tables=all_tables_count,
                    processed_tables=all_tables_count
                ), None
                
                try:
                    for schema_name in target_schemas:
                        fks = await self.get_foreign_keys(schema_name)
                        result.foreign_keys.extend(fks)
                except Exception as e:
                    logger.warning(f"외래키 추출 실패: {e}")
            
            # 완료
            yield ExtractionProgress(
                phase="complete",
                message=f"추출 완료: {total_schemas}개 스키마, {all_tables_count}개 테이블, {len(result.foreign_keys)}개 외래키",
                progress=100,
                total_schemas=total_schemas,
                processed_schemas=total_schemas,
                total_tables=all_tables_count,
                processed_tables=all_tables_count
            ), result
            
        except Exception as e:
            logger.error(f"메타데이터 추출 실패: {e}")
            yield ExtractionProgress(
                phase="error",
                message=f"오류 발생: {str(e)}",
                progress=0,
                error=str(e)
            ), None
        finally:
            await self.disconnect()


# ============================================================================
# PostgreSQL 어댑터
# ============================================================================

class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL 메타데이터 추출 어댑터"""
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self.connection = await asyncpg.connect(
                host=self.connection_params.get('host', 'localhost'),
                port=self.connection_params.get('port', 5432),
                user=self.connection_params.get('user'),
                password=self.connection_params.get('password'),
                database=self.connection_params.get('database')
            )
            return True
        except ImportError:
            # Fallback to psycopg2
            import psycopg2
            self.connection = psycopg2.connect(
                host=self.connection_params.get('host', 'localhost'),
                port=self.connection_params.get('port', 5432),
                user=self.connection_params.get('user'),
                password=self.connection_params.get('password'),
                dbname=self.connection_params.get('database')
            )
            self._use_sync = True
            return True
    
    async def disconnect(self) -> None:
        if self.connection:
            if hasattr(self, '_use_sync') and self._use_sync:
                self.connection.close()
            else:
                await self.connection.close()
            self.connection = None
    
    async def test_connection(self) -> tuple[bool, Optional[str]]:
        try:
            await self.connect()
            await self.disconnect()
            return True, None
        except Exception as e:
            return False, str(e)
    
    async def _execute(self, query: str, *args):
        """쿼리 실행 (동기/비동기 호환)"""
        if hasattr(self, '_use_sync') and self._use_sync:
            cursor = self.connection.cursor()
            cursor.execute(query, args if args else None)
            result = cursor.fetchall()
            cursor.close()
            return result
        else:
            return await self.connection.fetch(query, *args)
    
    async def get_schemas(self) -> List[str]:
        query = """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name
        """
        rows = await self._execute(query)
        return [row[0] if isinstance(row, tuple) else row['schema_name'] for row in rows]
    
    async def get_tables(self, schema: str) -> List[TableMetadata]:
        query = """
            SELECT 
                t.table_name,
                t.table_type,
                obj_description((quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass) as description
            FROM information_schema.tables t
            WHERE t.table_schema = $1
            AND t.table_type IN ('BASE TABLE', 'VIEW')
            ORDER BY t.table_name
        """
        
        if hasattr(self, '_use_sync') and self._use_sync:
            cursor = self.connection.cursor()
            cursor.execute(query.replace('$1', '%s'), (schema,))
            rows = cursor.fetchall()
            cursor.close()
        else:
            rows = await self.connection.fetch(query, schema)
        
        tables = []
        for row in rows:
            if isinstance(row, tuple):
                name, table_type, desc = row[0], row[1], row[2] if len(row) > 2 else None
            else:
                name, table_type, desc = row['table_name'], row['table_type'], row.get('description')
            
            tables.append(TableMetadata(
                name=name,
                schema=schema,
                table_type='VIEW' if 'VIEW' in table_type else 'TABLE',
                description=desc
            ))
        
        return tables
    
    async def get_columns(self, schema: str, table: str) -> List[ColumnMetadata]:
        query = """
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.ordinal_position,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                col_description((quote_ident($1) || '.' || quote_ident($2))::regclass, c.ordinal_position) as description,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name 
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_schema = $1
                AND tc.table_name = $2
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_schema = $1 AND c.table_name = $2
            ORDER BY c.ordinal_position
        """
        
        if hasattr(self, '_use_sync') and self._use_sync:
            cursor = self.connection.cursor()
            sync_query = query.replace('$1', '%s').replace('$2', '%s')
            cursor.execute(sync_query, (schema, table, schema, table, schema, table))
            rows = cursor.fetchall()
            cursor.close()
        else:
            rows = await self.connection.fetch(query, schema, table)
        
        columns = []
        for row in rows:
            if isinstance(row, tuple):
                columns.append(ColumnMetadata(
                    name=row[0],
                    data_type=row[1],
                    nullable=row[2] == 'YES',
                    default_value=row[3],
                    ordinal_position=row[4],
                    max_length=row[5],
                    numeric_precision=row[6],
                    numeric_scale=row[7],
                    description=row[8] if len(row) > 8 else None,
                    primary_key=row[9] if len(row) > 9 else False
                ))
            else:
                columns.append(ColumnMetadata(
                    name=row['column_name'],
                    data_type=row['data_type'],
                    nullable=row['is_nullable'] == 'YES',
                    default_value=row['column_default'],
                    ordinal_position=row['ordinal_position'],
                    max_length=row['character_maximum_length'],
                    numeric_precision=row['numeric_precision'],
                    numeric_scale=row['numeric_scale'],
                    description=row.get('description'),
                    primary_key=row.get('is_primary_key', False)
                ))
        
        return columns
    
    async def get_foreign_keys(self, schema: str = None) -> List[ForeignKeyMetadata]:
        query = """
            SELECT
                tc.constraint_name,
                tc.table_schema as source_schema,
                tc.table_name as source_table,
                kcu.column_name as source_column,
                ccu.table_schema as target_schema,
                ccu.table_name as target_table,
                ccu.column_name as target_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
        """
        
        if schema:
            query += f" AND tc.table_schema = '{schema}'"
        
        query += " ORDER BY tc.constraint_name"
        
        if hasattr(self, '_use_sync') and self._use_sync:
            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
        else:
            rows = await self.connection.fetch(query)
        
        foreign_keys = []
        for row in rows:
            if isinstance(row, tuple):
                foreign_keys.append(ForeignKeyMetadata(
                    name=row[0],
                    source_schema=row[1],
                    source_table=row[2],
                    source_column=row[3],
                    target_schema=row[4],
                    target_table=row[5],
                    target_column=row[6]
                ))
            else:
                foreign_keys.append(ForeignKeyMetadata(
                    name=row['constraint_name'],
                    source_schema=row['source_schema'],
                    source_table=row['source_table'],
                    source_column=row['source_column'],
                    target_schema=row['target_schema'],
                    target_table=row['target_table'],
                    target_column=row['target_column']
                ))
        
        return foreign_keys


# ============================================================================
# MySQL 어댑터
# ============================================================================

class MySQLAdapter(DatabaseAdapter):
    """MySQL 메타데이터 추출 어댑터"""
    
    async def connect(self) -> bool:
        try:
            import aiomysql
            self.connection = await aiomysql.connect(
                host=self.connection_params.get('host', 'localhost'),
                port=self.connection_params.get('port', 3306),
                user=self.connection_params.get('user'),
                password=self.connection_params.get('password'),
                db=self.connection_params.get('database')
            )
            return True
        except ImportError:
            import pymysql
            self.connection = pymysql.connect(
                host=self.connection_params.get('host', 'localhost'),
                port=self.connection_params.get('port', 3306),
                user=self.connection_params.get('user'),
                password=self.connection_params.get('password'),
                database=self.connection_params.get('database')
            )
            self._use_sync = True
            return True
    
    async def disconnect(self) -> None:
        if self.connection:
            if hasattr(self, '_use_sync') and self._use_sync:
                self.connection.close()
            else:
                self.connection.close()
            self.connection = None
    
    async def test_connection(self) -> tuple[bool, Optional[str]]:
        try:
            await self.connect()
            await self.disconnect()
            return True, None
        except Exception as e:
            return False, str(e)
    
    async def _execute(self, query: str):
        if hasattr(self, '_use_sync') and self._use_sync:
            cursor = self.connection.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return result
        else:
            # aiomysql uses async context manager for cursor
            async with self.connection.cursor() as cursor:
                await cursor.execute(query)
                result = await cursor.fetchall()
                return result
    
    async def get_schemas(self) -> List[str]:
        query = """
            SELECT SCHEMA_NAME 
            FROM INFORMATION_SCHEMA.SCHEMATA 
            WHERE SCHEMA_NAME NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
            ORDER BY SCHEMA_NAME
        """
        rows = await self._execute(query)
        return [row[0] for row in rows]
    
    async def get_tables(self, schema: str) -> List[TableMetadata]:
        query = f"""
            SELECT 
                TABLE_NAME,
                TABLE_TYPE,
                TABLE_COMMENT
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{schema}'
            AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
            ORDER BY TABLE_NAME
        """
        rows = await self._execute(query)
        
        tables = []
        for row in rows:
            tables.append(TableMetadata(
                name=row[0],
                schema=schema,
                table_type='VIEW' if 'VIEW' in row[1] else 'TABLE',
                description=row[2] if row[2] else None
            ))
        
        return tables
    
    async def get_columns(self, schema: str, table: str) -> List[ColumnMetadata]:
        query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                ORDINAL_POSITION,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                COLUMN_COMMENT,
                COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
            ORDER BY ORDINAL_POSITION
        """
        rows = await self._execute(query)
        
        columns = []
        for row in rows:
            columns.append(ColumnMetadata(
                name=row[0],
                data_type=row[1],
                nullable=row[2] == 'YES',
                default_value=row[3],
                ordinal_position=row[4],
                max_length=row[5],
                numeric_precision=row[6],
                numeric_scale=row[7],
                description=row[8] if row[8] else None,
                primary_key=row[9] == 'PRI'
            ))
        
        return columns
    
    async def get_foreign_keys(self, schema: str = None) -> List[ForeignKeyMetadata]:
        query = """
            SELECT
                CONSTRAINT_NAME,
                TABLE_SCHEMA as source_schema,
                TABLE_NAME as source_table,
                COLUMN_NAME as source_column,
                REFERENCED_TABLE_SCHEMA as target_schema,
                REFERENCED_TABLE_NAME as target_table,
                REFERENCED_COLUMN_NAME as target_column
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_NAME IS NOT NULL
        """
        
        if schema:
            query += f" AND TABLE_SCHEMA = '{schema}'"
        
        query += " ORDER BY CONSTRAINT_NAME"
        rows = await self._execute(query)
        
        foreign_keys = []
        for row in rows:
            foreign_keys.append(ForeignKeyMetadata(
                name=row[0],
                source_schema=row[1],
                source_table=row[2],
                source_column=row[3],
                target_schema=row[4],
                target_table=row[5],
                target_column=row[6]
            ))
        
        return foreign_keys


# ============================================================================
# 어댑터 팩토리
# ============================================================================

class AdapterFactory:
    """데이터베이스 어댑터 팩토리"""
    
    _adapters: Dict[str, type] = {
        'postgres': PostgreSQLAdapter,
        'postgresql': PostgreSQLAdapter,
        'mysql': MySQLAdapter,
        'mariadb': MySQLAdapter,
    }
    
    @classmethod
    def register(cls, engine_type: str, adapter_class: type):
        """어댑터 등록"""
        cls._adapters[engine_type.lower()] = adapter_class
    
    @classmethod
    def get_adapter(cls, engine_type: str, connection_params: Dict[str, Any]) -> Optional[DatabaseAdapter]:
        """어댑터 인스턴스 생성"""
        adapter_class = cls._adapters.get(engine_type.lower())
        if adapter_class:
            return adapter_class(connection_params)
        return None
    
    @classmethod
    def supported_engines(cls) -> List[str]:
        """지원하는 엔진 목록"""
        return list(cls._adapters.keys())


# ============================================================================
# 스키마 인트로스펙션 서비스
# ============================================================================

class SchemaIntrospectionService:
    """스키마 인트로스펙션 서비스"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def extract_and_store(
        self,
        datasource_name: str,
        engine: str,
        connection_params: Dict[str, Any],
        schemas: List[str] = None
    ) -> AsyncGenerator[ExtractionProgress, None]:
        """
        메타데이터 추출 및 Neo4j 저장
        """
        adapter = AdapterFactory.get_adapter(engine, connection_params)
        
        if not adapter:
            yield ExtractionProgress(
                phase="error",
                message=f"지원하지 않는 데이터베이스 엔진: {engine}",
                progress=0,
                error=f"Unsupported engine: {engine}"
            )
            return
        
        metadata = None
        
        async for progress, result in adapter.extract_metadata(schemas=schemas):
            yield progress
            if result:
                metadata = result
        
        if metadata and self.neo4j_service:
            yield ExtractionProgress(
                phase="storing",
                message="Neo4j에 메타데이터 저장 중...",
                progress=90
            )
            
            try:
                await self._store_to_neo4j(datasource_name, metadata)
                yield ExtractionProgress(
                    phase="complete",
                    message="메타데이터 저장 완료!",
                    progress=100,
                    total_schemas=len(metadata.schemas),
                    processed_schemas=len(metadata.schemas),
                    total_tables=sum(len(s.tables) for s in metadata.schemas),
                    processed_tables=sum(len(s.tables) for s in metadata.schemas)
                )
            except Exception as e:
                logger.error(f"Neo4j 저장 실패: {e}")
                yield ExtractionProgress(
                    phase="error",
                    message=f"Neo4j 저장 실패: {str(e)}",
                    progress=90,
                    error=str(e)
                )
    
    async def _store_to_neo4j(self, datasource_name: str, metadata: DatabaseMetadata):
        """Neo4j에 메타데이터 저장"""
        if not self.neo4j_service:
            return
        
        # 1. DataSource 노드 생성/업데이트
        await self.neo4j_service.create_datasource(
            name=datasource_name,
            engine=metadata.engine,
            parameters={
                "host": metadata.host,
                "port": metadata.port,
                "database": metadata.name
            },
            display_name=datasource_name
        )
        
        # 2. Schema 및 관계 생성
        for schema in metadata.schemas:
            await self.neo4j_service.execute_query(
                """
                MATCH (ds:DataSource {name: $datasource_name})
                MERGE (s:Schema {name: $schema_name, db: $database})
                SET s.description = $description
                MERGE (ds)-[:HAS_SCHEMA]->(s)
                """,
                {
                    "datasource_name": datasource_name,
                    "schema_name": schema.name,
                    "database": metadata.name,
                    "description": schema.description
                }
            )
            
            # 3. Table 및 관계 생성
            for table in schema.tables:
                await self.neo4j_service.execute_query(
                    """
                    MATCH (s:Schema {name: $schema_name, db: $database})
                    MERGE (t:Table {name: $table_name, schema: $schema_name})
                    SET t.table_type = $table_type,
                        t.description = $description,
                        t.db = $database,
                        t.datasource = $datasource_name
                    MERGE (s)-[:HAS_TABLE]->(t)
                    """,
                    {
                        "datasource_name": datasource_name,
                        "schema_name": schema.name,
                        "database": metadata.name,
                        "table_name": table.name,
                        "table_type": table.table_type,
                        "description": table.description
                    }
                )
                
                # 4. Column 생성 (fqn 기준 MERGE - robo-analyzer와 일관성 유지)
                for col in table.columns:
                    # fqn 생성: schema.table.column (소문자)
                    fqn = f"{schema.name}.{table.name}.{col.name}".lower()
                    
                    await self.neo4j_service.execute_query(
                        """
                        MATCH (t:Table {name: $table_name, schema: $schema_name})
                        MERGE (c:Column {fqn: $fqn})
                        ON CREATE SET 
                            c.name = $column_name,
                            c.table = $table_name,
                            c.schema = $schema_name
                        SET c.type = $data_type,
                            c.nullable = $nullable,
                            c.primary_key = $primary_key,
                            c.description = $description,
                            c.ordinal_position = $ordinal_position,
                            c.datasource = $datasource_name
                        MERGE (t)-[:HAS_COLUMN]->(c)
                        """,
                        {
                            "fqn": fqn,
                            "datasource_name": datasource_name,
                            "table_name": table.name,
                            "schema_name": schema.name,
                            "column_name": col.name,
                            "data_type": col.data_type,
                            "nullable": col.nullable,
                            "primary_key": col.primary_key,
                            "description": col.description,
                            "ordinal_position": col.ordinal_position
                        }
                    )
        
        # 5. Foreign Key 관계 생성 (fqn 기준 매칭)
        for fk in metadata.foreign_keys:
            source_fqn = f"{fk.source_schema}.{fk.source_table}.{fk.source_column}".lower()
            target_fqn = f"{fk.target_schema}.{fk.target_table}.{fk.target_column}".lower()
            
            await self.neo4j_service.execute_query(
                """
                MATCH (sc:Column {fqn: $source_fqn})
                MATCH (tc:Column {fqn: $target_fqn})
                MERGE (sc)-[r:REFERENCES]->(tc)
                SET r.constraint_name = $constraint_name
                """,
                {
                    "source_fqn": source_fqn,
                    "target_fqn": target_fqn,
                    "constraint_name": fk.name
                }
            )


# 서비스 인스턴스
schema_introspection_service = SchemaIntrospectionService()
