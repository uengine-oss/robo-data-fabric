"""Datasource table, schema, and sample browsing routes."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from .graph_connection import apply_neo4j_override
from fabric.gateway import fabric_gateway
from registry.datasources import datasource_registry

router = APIRouter(
    prefix="/datasources", tags=["Data Sources"],
    dependencies=[Depends(apply_neo4j_override)],
)
logger = logging.getLogger(__name__)


async def _require_datasource(name: str) -> None:
    if not await datasource_registry.get_datasource(name):
        raise HTTPException(status_code=404, detail=f"DataSource '{name}' not found")

@router.get("/{name}/tables")
async def get_tables(name: str) -> dict[str, Any]:
    await _require_datasource(name)
    try:
        tables = await fabric_gateway.get_tables(name)
    except RuntimeError as exc:
        logger.error("Datasource table listing failed", extra={"connector_name": name})
        raise HTTPException(status_code=502, detail="테이블 목록 조회에 실패했습니다.") from exc
    return {"tables": [{"name": table} for table in tables]}


# ⚠ 컬럼·표본은 **가상 노드를 선언한 뒤**에 보인다. 이 엔진에는 컬럼 목록을
#    주는 문장이 없고 `CREATE VIRTUAL NODE … KEY <컬럼>` 이 열쇠 이름을
#    요구한다(2026-10-27 실측). 그래서 몰래 임시 노드를 만들어 우회할 수 없다.
#    선언은 이 설계에서 **사람이 하는 모델링**이고, 안 된 표에는 그렇게 말한다.
@router.get("/{name}/tables/{table}/schema")
async def get_table_schema(name: str, table: str) -> dict[str, Any]:
    await _require_datasource(name)
    try:
        columns = await fabric_gateway.get_table_schema(name, table)
    except fabric_gateway.NotDeclared as exc:
        # 412 — 할 수 없는 것이 아니라 **아직 할 일이 남은** 것이다.
        raise HTTPException(status_code=412, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error(
            "Datasource schema lookup failed",
            extra={"connector_name": name, "table_name": table},
        )
        raise HTTPException(status_code=502, detail="테이블 스키마 조회에 실패했습니다.") from exc
    return {"table": table, "columns": columns}


@router.get("/{name}/tables/{table}/sample")
async def get_sample_data(name: str, table: str, limit: int = Query(10, ge=1, le=1000)) -> dict[str, Any]:
    await _require_datasource(name)
    try:
        result = await fabric_gateway.sample_data(name, table, limit)
    except fabric_gateway.NotDeclared as exc:
        raise HTTPException(status_code=412, detail=str(exc)) from exc
    if result["type"] == "error":
        raise HTTPException(status_code=400, detail="샘플 데이터 조회에 실패했습니다.")
    return {"columns": result["columns"], "data": result["data"], "total_rows": result["row_count"]}
