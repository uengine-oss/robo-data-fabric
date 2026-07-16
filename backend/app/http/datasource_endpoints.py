"""Data Fabric의 데이터소스 연결 registry와 실제 DB 접근 HTTP 경계."""
from __future__ import annotations

import logging
import os
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..contracts.datasource_api import DataSourceCreate, DataSourceList, DataSourceResponse
from ..connections.neo4j_context import Neo4jOverride, set_override
from ..connections.mindsdb_gateway import mindsdb_gateway
from ..connections.datasource_registry import datasource_registry


logger = logging.getLogger(__name__)
MINDSDB_REPLACE_LOCALHOST = os.getenv("MINDSDB_REPLACE_LOCALHOST", "host.docker.internal")


async def apply_neo4j_override(request: Request) -> None:
    """Electron이 선택한 Neo4j 연결을 요청 context에 설정한다."""
    set_override(Neo4jOverride.from_headers(request.headers))


router = APIRouter(
    prefix="/datasources",
    tags=["Data Sources"],
    dependencies=[Depends(apply_neo4j_override)],
)


class TestConnectionRequest(BaseModel):
    engine: str
    host: str = ""
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None


def _mindsdb_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """요청 사본만 MindsDB 네트워크 관점으로 정규화한다. 원본과 secret은 저장하지 않는다."""
    result = dict(parameters)
    host = result.get("host")
    if host in {"localhost", "127.0.0.1"} and MINDSDB_REPLACE_LOCALHOST:
        result["host"] = MINDSDB_REPLACE_LOCALHOST
    return result


def _registry_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """비밀 키가 registry 계층에 도달하지 않도록 HTTP 경계에서 allowlist한다."""
    allowed = {"host", "port", "database", "user", "username", "display_name"}
    return {key: value for key, value in parameters.items() if key in allowed}


@router.get("", response_model=DataSourceList)
async def list_datasources() -> dict[str, Any]:
    """비밀정보 없는 registry 목록을 반환한다."""
    return {"datasources": await datasource_registry.get_datasources()}


@router.post("/test-connection")
async def test_connection_params(request: TestConnectionRequest) -> dict[str, Any]:
    """credential을 저장하지 않고 임시 MindsDB 연결로 실제 접속을 검증한다."""
    probe_name = f"robo_probe_{uuid4().hex}"
    try:
        result = await mindsdb_gateway.create_database(
            probe_name,
            request.engine,
            _mindsdb_parameters(request.model_dump(exclude={"engine"}, exclude_none=True)),
        )
        if result["type"] == "error":
            return {"success": False, "message": "데이터베이스 연결에 실패했습니다."}
        return {"success": True, "message": "데이터베이스 연결에 성공했습니다."}
    finally:
        try:
            cleanup = await mindsdb_gateway.drop_database(probe_name)
        except Exception:
            logger.error("temporary MindsDB connection cleanup failed", extra={"probe_name": probe_name})
        else:
            if cleanup["type"] == "error":
                logger.error("temporary MindsDB connection cleanup failed", extra={"probe_name": probe_name})


@router.post("", response_model=DataSourceResponse)
async def create_datasource(datasource: DataSourceCreate, request: Request) -> dict[str, Any]:
    """MindsDB 연결과 Neo4j registry를 하나의 보상 가능한 생성 작업으로 등록한다."""
    if await datasource_registry.get_datasource(datasource.name):
        raise HTTPException(status_code=409, detail=f"DataSource '{datasource.name}' already exists")

    mindsdb_result = await mindsdb_gateway.create_database(
        datasource.name,
        datasource.engine,
        _mindsdb_parameters(datasource.parameters),
    )
    if mindsdb_result["type"] == "error":
        raise HTTPException(status_code=400, detail="데이터베이스 연결 등록에 실패했습니다.")

    try:
        registry = await datasource_registry.create_datasource(
            name=datasource.name,
            engine=datasource.engine,
            parameters=_registry_parameters(datasource.parameters),
            display_name=datasource.parameters.get("display_name", datasource.name),
            workspace_id=request.headers.get("x-workspace-id", "default"),
        )
        if not registry:
            raise RuntimeError("registry returned no datasource")
    except Exception as exc:
        compensation = await mindsdb_gateway.drop_database(datasource.name)
        if compensation["type"] == "error":
            logger.error("datasource create compensation failed", extra={"datasource": datasource.name})
        raise HTTPException(status_code=500, detail="연결 registry 저장에 실패했습니다.") from exc

    return registry


@router.get("/{name}/health")
async def check_health(name: str) -> dict[str, Any]:
    datasource = await datasource_registry.get_datasource(name)
    if not datasource:
        return {
            "name": name,
            "status": "not_found",
            "message": "데이터소스를 찾을 수 없습니다.",
            "db_connected": False,
            "mindsdb_connected": False,
        }

    result = await mindsdb_gateway.inspect_database(name)
    healthy = result["success"]
    return {
        "name": name,
        "status": "healthy" if healthy else "disconnected",
        "message": "MindsDB를 통한 실제 DB 접근 정상" if healthy else "실제 DB 접근 실패",
        "db_connected": healthy,
        "mindsdb_connected": healthy,
    }


@router.post("/{name}/test")
async def test_connection(name: str) -> dict[str, Any]:
    result = await mindsdb_gateway.inspect_database(name)
    return {
        "success": result["success"],
        "message": (
            f"Connected successfully. Found {result['table_count']} tables."
            if result["success"]
            else "Database connection failed."
        ),
    }


@router.get("/{name}")
async def get_datasource(name: str) -> dict[str, Any]:
    datasource = await datasource_registry.get_datasource(name)
    if not datasource:
        raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found")
    return datasource


@router.delete("/{name}")
async def delete_datasource(name: str) -> dict[str, str]:
    """기본 동작으로 MindsDB 연결과 registry를 함께 제거한다."""
    datasource = await datasource_registry.get_datasource(name)
    if not datasource:
        raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found")

    mindsdb_result = await mindsdb_gateway.drop_database(name)
    registry_deleted = await datasource_registry.delete_datasource(name)
    if mindsdb_result["type"] == "error" or not registry_deleted:
        raise HTTPException(status_code=502, detail="데이터소스 삭제가 부분 실패했습니다. 다시 시도해 주세요.")
    return {"message": f"Data source '{name}' deleted successfully"}


@router.get("/{name}/tables")
async def get_tables(name: str) -> dict[str, Any]:
    tables = await mindsdb_gateway.get_tables(name)
    return {"tables": [{"name": table} for table in tables]}


@router.get("/{name}/tables/{table}/schema")
async def get_table_schema(name: str, table: str) -> dict[str, Any]:
    return {"table": table, "columns": await mindsdb_gateway.get_table_schema(name, table)}


@router.get("/{name}/tables/{table}/sample")
async def get_sample_data(name: str, table: str, limit: int = Query(10, ge=1, le=1000)) -> dict[str, Any]:
    result = await mindsdb_gateway.sample_data(name, table, limit)
    if result["type"] == "error":
        raise HTTPException(status_code=400, detail="샘플 데이터 조회에 실패했습니다.")
    return {"columns": result["columns"], "data": result["data"], "total_rows": result["row_count"]}


@router.on_event("startup")
async def startup() -> None:
    await datasource_registry.ensure_constraints()


@router.on_event("shutdown")
async def shutdown() -> None:
    await datasource_registry.close()
