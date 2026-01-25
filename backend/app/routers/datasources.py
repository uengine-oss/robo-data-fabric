"""Data Sources Router - Neo4j & MindsDB 통합"""
import json
import logging
import os
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from dataclasses import asdict
from pydantic import BaseModel
from ..schemas.datasource import (
    DataSourceCreate, 
    DataSourceResponse, 
    DataSourceList,
    TableInfo,
    TableData,
    DATASOURCE_CONFIGS,
    DataSourceType
)
from ..services.mindsdb_service import mindsdb_service
from ..services.neo4j_service import neo4j_service
from ..services.schema_introspection import (
    SchemaIntrospectionService,
    AdapterFactory,
    ExtractionProgress
)

logger = logging.getLogger(__name__)

# 환경변수: localhost를 MindsDB용 Docker 내부 호스트로 대치
# 예: MINDSDB_REPLACE_LOCALHOST=host.docker.internal
MINDSDB_REPLACE_LOCALHOST = os.getenv("MINDSDB_REPLACE_LOCALHOST", "host.docker.internal")
router = APIRouter(prefix="/datasources", tags=["Data Sources"])


class ExtractMetadataRequest(BaseModel):
    """메타데이터 추출 요청 모델"""
    schemas: Optional[List[str]] = None
    password: Optional[str] = None  # 재인증 시 패스워드 전달

# 스키마 인트로스펙션 서비스 초기화
introspection_service = SchemaIntrospectionService(neo4j_service)


@router.get("/types")
async def get_datasource_types():
    """Get all supported data source types with their configuration"""
    types = []
    for source_type, config in DATASOURCE_CONFIGS.items():
        types.append({
            "type": source_type.value,
            "display_name": config["display_name"],
            "icon": config["icon"],
            "fields": config["fields"]
        })
    return {"types": types}


@router.get("/supported-engines")
async def get_supported_engines():
    """Get list of engines that support metadata extraction"""
    return {"engines": AdapterFactory.supported_engines()}


@router.get("", response_model=DataSourceList)
async def list_datasources(source: str = Query("neo4j", description="Data source: 'neo4j' or 'mindsdb'")):
    """Get list of all registered data sources"""
    if source == "mindsdb":
        # MindsDB에서 데이터 소스 조회
        databases = await mindsdb_service.get_databases()
        return {"datasources": databases}
    else:
        # Neo4j에서 DataSource 노드 조회
        datasources = await neo4j_service.get_datasources()
        return {"datasources": [
            {
                "name": ds["name"],
                "engine": ds.get("engine", "unknown"),
                "tables": [],
                "display_name": ds.get("display_name"),
                "host": ds.get("host"),
                "port": ds.get("port"),
                "database": ds.get("database"),
                "user": ds.get("user"),
                "schema_count": ds.get("schema_count", 0)
            }
            for ds in datasources
        ]}


@router.get("/{name}/health")
async def check_health(name: str):
    """데이터소스 연결 상태 확인 (헬스체크)"""
    # Neo4j에서 연결 정보 조회
    connection = await neo4j_service.get_connection_params(name)
    if not connection:
        return {
            "name": name,
            "status": "not_found",
            "message": "데이터소스를 찾을 수 없습니다",
            "db_connected": False,
            "mindsdb_connected": False
        }
    
    engine = connection.get("engine", "").lower()
    result = {
        "name": name,
        "status": "unknown",
        "message": "",
        "db_connected": False,
        "mindsdb_connected": False
    }
    
    # 1. 실제 DB 연결 테스트
    if engine in AdapterFactory.supported_engines():
        try:
            adapter = AdapterFactory.get_adapter(engine, connection)
            if adapter:
                await adapter.connect()
                await adapter.disconnect()
                result["db_connected"] = True
                result["status"] = "healthy"
                result["message"] = "데이터베이스 연결 정상"
        except Exception as e:
            result["db_connected"] = False
            result["status"] = "disconnected"
            result["message"] = f"연결 실패: {str(e)}"
    else:
        result["message"] = f"지원하지 않는 엔진: {engine}"
    
    # 2. MindsDB 등록 여부 확인 (데이터베이스 목록에서 확인)
    try:
        mindsdb_databases = await mindsdb_service.get_databases()
        mindsdb_names = [db["name"] for db in mindsdb_databases]
        result["mindsdb_connected"] = name in mindsdb_names
    except Exception as e:
        logger.warning(f"MindsDB 연결 확인 실패: {e}")
        result["mindsdb_connected"] = False
    
    # 최종 상태 결정
    if result["db_connected"] and result["mindsdb_connected"]:
        result["status"] = "healthy"
        result["message"] = "DB 및 MindsDB 연결 정상"
    elif result["db_connected"]:
        result["status"] = "partial"
        result["message"] = "DB 연결됨, MindsDB 미등록"
    elif result["mindsdb_connected"]:
        result["status"] = "partial"
        result["message"] = "MindsDB 등록됨, DB 연결 실패"
    else:
        result["status"] = "disconnected"
        if not result["message"]:
            result["message"] = "연결 없음"
    
    return result


@router.post("", response_model=DataSourceResponse)
async def create_datasource(
    datasource: DataSourceCreate,
    register_to: str = Query("both", description="Register to: 'neo4j', 'mindsdb', or 'both'")
):
    """Create a new data source connection
    
    순서:
    1. Neo4j에 메타데이터 저장 (비밀번호 포함)
    2. MindsDB에 등록 (연결 검증은 MindsDB가 수행)
    """
    mindsdb_error = None
    
    # 1. Neo4j에 DataSource 노드 등록 (비밀번호 포함)
    if register_to in ["neo4j", "both"]:
        neo4j_result = await neo4j_service.create_datasource(
            name=datasource.name,
            engine=datasource.engine.value,
            parameters=datasource.parameters,  # 비밀번호 포함
            display_name=datasource.parameters.get("display_name", datasource.name)
        )
        if not neo4j_result:
            raise HTTPException(status_code=400, detail="Failed to create DataSource in Neo4j")
        
        logger.info(f"Neo4j DataSource created: {datasource.name}")
    
    # 2. MindsDB에 등록 (연결 검증은 MindsDB가 수행)
    if register_to in ["mindsdb", "both"]:
        try:
            # 기존 연결이 있으면 삭제
            await mindsdb_service.drop_database(datasource.name)
            
            # MindsDB용 파라미터 준비
            mindsdb_params = datasource.parameters.copy()
            
            # localhost를 Docker 내부 호스트로 자동 대치
            # MindsDB는 Docker 컨테이너에서 실행되므로 localhost가 다른 의미를 가짐
            host = mindsdb_params.get("host", "")
            if host in ["localhost", "127.0.0.1"] and MINDSDB_REPLACE_LOCALHOST:
                mindsdb_params["host"] = MINDSDB_REPLACE_LOCALHOST
                logger.info(f"Replacing localhost with {MINDSDB_REPLACE_LOCALHOST} for MindsDB")
            
            logger.info(f"MindsDB registration with host: {mindsdb_params.get('host')}")
            
            # MindsDB에 등록 - 이 과정에서 연결 검증됨
            mindsdb_result = await mindsdb_service.create_database(
                name=datasource.name,
                engine=datasource.engine.value,
                parameters=mindsdb_params
            )
            
            if mindsdb_result["type"] == "error":
                mindsdb_error = mindsdb_result.get("error", "MindsDB 등록 실패")
                logger.warning(f"MindsDB registration failed: {mindsdb_error}")
                # MindsDB 실패해도 Neo4j 등록은 유지, 에러 메시지 반환
                raise HTTPException(
                    status_code=400, 
                    detail=f"연결 실패: {mindsdb_error}"
                )
            else:
                logger.info(f"MindsDB database created: {datasource.name}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"MindsDB registration failed: {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"연결 실패: {str(e)}"
            )
    
    return {
        "name": datasource.name,
        "engine": datasource.engine.value,
        "tables": []
    }


@router.get("/{name}")
async def get_datasource(name: str, source: str = Query("neo4j")):
    """Get details of a specific data source"""
    if source == "neo4j":
        datasource = await neo4j_service.get_datasource(name)
        if not datasource:
            raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found")
        return datasource
    else:
        # MindsDB에서는 테이블 목록으로 확인
        tables = await mindsdb_service.get_tables(name)
        return {"name": name, "tables": tables}


@router.delete("/{name}")
async def delete_datasource(
    name: str, 
    delete_from: str = Query("neo4j", description="Delete from: 'neo4j', 'mindsdb', or 'both'")
):
    """Delete a data source connection"""
    deleted = False
    
    if delete_from in ["neo4j", "both"]:
        deleted = await neo4j_service.delete_datasource(name)
    
    if delete_from in ["mindsdb", "both"]:
        result = await mindsdb_service.drop_database(name)
        if result["type"] != "error":
            deleted = True
    
    if not deleted:
        raise HTTPException(status_code=400, detail=f"Failed to delete DataSource '{name}'")
    
    return {"message": f"Data source '{name}' deleted successfully"}


class UpdateConnectionRequest(BaseModel):
    """연결 정보 업데이트 요청"""
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None


@router.put("/{name}/connection")
async def update_connection(name: str, request: UpdateConnectionRequest):
    """데이터소스 연결 정보 업데이트 (비밀번호 포함)"""
    # 업데이트할 파라미터만 추출
    params = {k: v for k, v in request.model_dump().items() if v is not None}
    
    if not params:
        raise HTTPException(status_code=400, detail="No parameters to update")
    
    result = await neo4j_service.update_datasource(name, parameters=params)
    if not result:
        raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found")
    
    return {"message": "Connection info updated", "datasource": result}


@router.get("/{name}/schemas")
async def get_schemas(name: str):
    """Get list of schemas in a data source (Neo4j only)"""
    schemas = await neo4j_service.get_schemas(name)
    return {"schemas": schemas}


@router.get("/{name}/connection")
async def get_connection_params(name: str):
    """Get connection parameters for a data source (internal use for extraction)"""
    params = await neo4j_service.get_connection_params(name)
    if not params:
        raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found")
    return params


@router.get("/{name}/tables")
async def get_tables(name: str, schema: str = Query(None), source: str = Query("neo4j")):
    """Get list of tables in a data source"""
    if source == "neo4j":
        tables = await neo4j_service.get_tables(name, schema)
        return {"tables": tables}
    else:
        tables = await mindsdb_service.get_tables(name)
        return {"tables": [{"name": t} for t in tables]}


@router.get("/{name}/tables/{table}/schema")
async def get_table_schema(name: str, table: str, source: str = Query("mindsdb")):
    """Get schema of a specific table (MindsDB only for now)"""
    columns = await mindsdb_service.get_table_schema(name, table)
    return {"table": table, "columns": columns}


@router.get("/{name}/tables/{table}/sample")
async def get_sample_data(name: str, table: str, limit: int = 10, source: str = Query("mindsdb")):
    """Get sample data from a table (MindsDB only for now)"""
    result = await mindsdb_service.sample_data(name, table, limit)
    
    if result["type"] == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "columns": result["columns"],
        "data": result["data"],
        "total_rows": result["row_count"]
    }


@router.post("/{name}/test")
async def test_connection(name: str, source: str = Query("mindsdb")):
    """Test connection to a data source"""
    if source == "mindsdb":
        tables = await mindsdb_service.get_tables(name)
        
        if not tables:
            result = await mindsdb_service.execute_query(f"SELECT 1 FROM {name}.dual")
            if result["type"] == "error":
                return {"success": False, "message": result["error"]}
        
        return {"success": True, "message": f"Connected successfully. Found {len(tables)} tables."}
    else:
        # Neo4j에서는 DataSource 노드 존재 여부 확인
        datasource = await neo4j_service.get_datasource(name)
        if datasource:
            return {"success": True, "message": f"DataSource '{name}' registered in Neo4j"}
        return {"success": False, "message": f"DataSource '{name}' not found in Neo4j"}


# ========================================
# Schema Introspection (메타데이터 추출)
# ========================================


@router.post("/{name}/extract-metadata")
async def extract_metadata(
    name: str,
    request: ExtractMetadataRequest = None
):
    """
    데이터 소스에서 메타데이터 추출 및 Neo4j에 저장 (스트리밍)
    
    저장된 연결 정보를 사용하여 데이터베이스에 연결하고
    테이블, 컬럼, 외래키 정보를 추출하여 Neo4j에 저장합니다.
    
    패스워드가 요청에 포함되면 해당 패스워드를 사용하고 Neo4j에도 업데이트합니다.
    Progress 이벤트를 SSE(Server-Sent Events)로 스트리밍합니다.
    """
    # 저장된 연결 정보 조회
    connection = await neo4j_service.get_connection_params(name)
    if not connection:
        raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found or no connection info")
    
    # 패스워드가 요청에 있으면 오버라이드하고 Neo4j에 업데이트
    if request and request.password:
        connection["password"] = request.password
        # Neo4j에 패스워드 업데이트 (upsert)
        await neo4j_service.update_datasource(name, parameters={"password": request.password})
        logger.info(f"Password updated for datasource: {name}")
    
    engine = connection.get("engine", "postgres")
    schemas = request.schemas if request else None
    
    # 지원하는 엔진인지 확인
    if engine.lower() not in AdapterFactory.supported_engines():
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported engine: {engine}. Supported: {AdapterFactory.supported_engines()}"
        )
    
    async def generate_events():
        """SSE 이벤트 생성"""
        try:
            async for progress in introspection_service.extract_and_store(
                datasource_name=name,
                engine=engine,
                connection_params=connection,
                schemas=schemas
            ):
                event_data = {
                    "phase": progress.phase,
                    "message": progress.message,
                    "progress": progress.progress,
                    "total_schemas": progress.total_schemas,
                    "processed_schemas": progress.processed_schemas,
                    "total_tables": progress.total_tables,
                    "processed_tables": progress.processed_tables,
                    "error": progress.error
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            error_event = {
                "phase": "error",
                "message": str(e),
                "progress": 0,
                "error": str(e)
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{name}/extract-metadata-sync")
async def extract_metadata_sync(
    name: str,
    request: ExtractMetadataRequest = None
):
    """
    데이터 소스에서 메타데이터 추출 (동기식, non-streaming)
    
    저장된 연결 정보를 사용합니다.
    패스워드가 요청에 포함되면 해당 패스워드를 사용하고 Neo4j에도 업데이트합니다.
    테스트용 또는 작은 데이터베이스에 적합합니다.
    """
    # 저장된 연결 정보 조회
    connection = await neo4j_service.get_connection_params(name)
    if not connection:
        raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found or no connection info")
    
    # 패스워드가 요청에 있으면 오버라이드하고 Neo4j에 업데이트
    if request and request.password:
        connection["password"] = request.password
        # Neo4j에 패스워드 업데이트 (upsert)
        await neo4j_service.update_datasource(name, parameters={"password": request.password})
        logger.info(f"Password updated for datasource: {name}")
    
    engine = connection.get("engine", "postgres")
    schemas = request.schemas if request else None
    
    if engine.lower() not in AdapterFactory.supported_engines():
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported engine: {engine}"
        )
    
    last_progress = None
    try:
        async for progress in introspection_service.extract_and_store(
            datasource_name=name,
            engine=engine,
            connection_params=connection,
            schemas=schemas
        ):
            last_progress = progress
            if progress.error:
                raise HTTPException(status_code=500, detail=progress.error)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if last_progress:
        return {
            "success": last_progress.phase == "complete",
            "message": last_progress.message,
            "schemas": last_progress.total_schemas,
            "tables": last_progress.total_tables
        }
    
    return {"success": False, "message": "No progress data"}


# ========================================
# Startup/Shutdown Hooks
# ========================================

@router.on_event("startup")
async def startup():
    """서비스 시작 시 Neo4j 제약조건 생성"""
    try:
        await neo4j_service.ensure_constraints()
    except Exception as e:
        print(f"Warning: Could not create Neo4j constraints: {e}")


@router.on_event("shutdown")
async def shutdown():
    """서비스 종료 시 Neo4j 드라이버 정리"""
    await neo4j_service.close()
