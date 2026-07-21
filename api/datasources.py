"""Data Fabric의 데이터소스 연결 registry와 실제 DB 접근 HTTP 경계."""
from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from contracts.datasources import (
    DataSourceCreate, DataSourceList, DataSourceResponse, TestConnectionRequest,
)
from .graph_connection import apply_neo4j_override
from credentials.allowlist import registry_parameters
from credentials.network_rewrite import mindsdb_parameters
from mindsdb.transport import mindsdb_gateway
from registry.datasources import datasource_registry
from shared.config.settings import settings


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/datasources",
    tags=["Data Sources"],
    dependencies=[Depends(apply_neo4j_override)],
)


async def _drop_mindsdb_connection(name: str, *, operation: str) -> bool:
    """부분 실패 시 MindsDB 연결을 정리하고 정리 실패를 관측 가능하게 남긴다."""
    try:
        result = await mindsdb_gateway.drop_database(name)
    except Exception:
        logger.exception(
            "MindsDB connection cleanup raised",
            extra={"connector_name": name, "operation": operation},
        )
        return False
    if result["type"] == "error":
        logger.error(
            "MindsDB connection cleanup failed",
            extra={"connector_name": name, "operation": operation},
        )
        return False
    return True


async def _create_or_replace_stale_connection(
    name: str, engine: str, parameters: dict[str, Any]
) -> bool:
    """Create a connector, repairing an orphan left without a registry node."""
    result = await mindsdb_gateway.create_database(name, engine, parameters)
    if result["type"] != "error":
        return True

    try:
        existing = await mindsdb_gateway.inspect_database(name)
    except Exception:
        return False
    if not existing["success"]:
        return False

    logger.warning(
        "Replacing orphan MindsDB connector without registry ownership",
        extra={"connector_name": name},
    )
    if not await _drop_mindsdb_connection(name, operation="replace_orphan"):
        raise HTTPException(status_code=502, detail="기존 고아 연결 정리에 실패했습니다.")
    retry = await mindsdb_gateway.create_database(name, engine, parameters)
    return retry["type"] != "error"


@router.get("", response_model=DataSourceList)
async def list_datasources() -> dict[str, Any]:
    """비밀정보 없는 registry 목록을 반환한다."""
    return {"datasources": await datasource_registry.get_datasources()}


@router.post("/test-connection")
async def test_connection_params(request: TestConnectionRequest) -> dict[str, Any]:
    """credential을 저장하지 않고 임시 MindsDB 연결로 실제 접속을 검증한다."""
    probe_name = f"robo_probe_{uuid4().hex}"
    created = False
    try:
        result = await mindsdb_gateway.create_database(
            probe_name,
            request.engine,
            mindsdb_parameters(
                request.model_dump(exclude={"engine"}, exclude_none=True),
                settings.mindsdb_replace_localhost,
            ),
        )
        if result["type"] == "error":
            return {"success": False, "message": "데이터베이스 연결에 실패했습니다."}
        created = True
        try:
            inspection = await mindsdb_gateway.inspect_database(probe_name)
        except Exception as exc:
            logger.warning(
                "Datasource connection probe failed",
                extra={"error_type": type(exc).__name__},
            )
            return {"success": False, "message": "데이터베이스 연결에 실패했습니다."}
        if not inspection["success"]:
            return {"success": False, "message": "데이터베이스 연결에 실패했습니다."}
        return {"success": True, "message": "데이터베이스 연결에 성공했습니다."}
    finally:
        if created and not await _drop_mindsdb_connection(
            probe_name, operation="connection_probe"
        ):
            raise HTTPException(
                status_code=502,
                detail="임시 연결 정리에 실패했습니다. 다시 시도해 주세요.",
            )


@router.post("", response_model=DataSourceResponse)
async def create_datasource(datasource: DataSourceCreate, request: Request) -> dict[str, Any]:
    """MindsDB 연결과 Neo4j registry를 하나의 보상 가능한 생성 작업으로 등록한다."""
    if await datasource_registry.get_datasource(datasource.name):
        raise HTTPException(status_code=409, detail=f"DataSource '{datasource.name}' already exists")

    created = await _create_or_replace_stale_connection(
        datasource.name,
        datasource.engine,
        mindsdb_parameters(datasource.parameters, settings.mindsdb_replace_localhost),
    )
    if not created:
        raise HTTPException(status_code=400, detail="데이터베이스 연결 등록에 실패했습니다.")

    try:
        inspection = await mindsdb_gateway.inspect_database(datasource.name)
    except Exception as exc:
        if not await _drop_mindsdb_connection(datasource.name, operation="target_inspection"):
            raise HTTPException(status_code=502, detail="실패한 연결 정리에 실패했습니다.") from exc
        raise HTTPException(status_code=400, detail="대상 데이터베이스에 연결할 수 없습니다.") from exc
    if not inspection["success"]:
        if not await _drop_mindsdb_connection(datasource.name, operation="target_inspection"):
            raise HTTPException(status_code=502, detail="실패한 연결 정리에 실패했습니다.")
        raise HTTPException(status_code=400, detail="대상 데이터베이스에 연결할 수 없습니다.")

    try:
        registry = await datasource_registry.create_datasource(
            name=datasource.name,
            engine=datasource.engine,
            parameters=registry_parameters(datasource.parameters),
            display_name=datasource.parameters.get("display_name", datasource.name),
            workspace_id=request.headers.get("x-workspace-id", "default"),
        )
        if not registry:
            raise RuntimeError("registry returned no datasource")
    except Exception as exc:
        if not await _drop_mindsdb_connection(datasource.name, operation="registry_create"):
            raise HTTPException(status_code=500, detail="연결 등록과 보상 정리가 모두 실패했습니다.") from exc
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
    if not await datasource_registry.get_datasource(name):
        raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found")
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
    if mindsdb_result["type"] == "error":
        raise HTTPException(status_code=502, detail="MindsDB 연결 삭제에 실패했습니다. 다시 시도해 주세요.")
    registry_deleted = await datasource_registry.delete_datasource(name)
    if not registry_deleted:
        raise HTTPException(status_code=502, detail="데이터소스 삭제가 부분 실패했습니다. 다시 시도해 주세요.")
    return {"message": f"Data source '{name}' deleted successfully"}


@router.on_event("startup")
async def startup() -> None:
    await datasource_registry.ensure_constraints()


@router.on_event("shutdown")
async def shutdown() -> None:
    await datasource_registry.close()
