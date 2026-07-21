"""MindsDB SQL 실행과 상태 확인 HTTP 경계."""

from fastapi import APIRouter, Depends, HTTPException

from api.graph_connection import apply_neo4j_override
from contracts.query import MindsDBStatus, QueryRequest, QueryResponse
from mindsdb.transport import mindsdb_gateway
from queries.builder import build_mindsdb_read_query
from queries.policy import ReadOnlyQueryError
from registry.datasources import datasource_registry


router = APIRouter(
    prefix="/query",
    tags=["Query"],
    dependencies=[Depends(apply_neo4j_override)],
)


@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """MindsDB를 통해 대상 데이터소스 SQL을 실행한다."""
    if not await datasource_registry.get_datasource(request.datasource):
        raise HTTPException(status_code=404, detail="DataSource not found")
    try:
        native_query = build_mindsdb_read_query(
            request.datasource, request.query, request.max_rows
        )
    except ReadOnlyQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = await mindsdb_gateway.execute_query(native_query)
    return QueryResponse(**result)


@router.get("/status", response_model=MindsDBStatus)
async def get_status():
    """MindsDB 연결 상태를 반환한다."""
    connected, version, error = await mindsdb_gateway.check_connection()
    return MindsDBStatus(connected=connected, version=version, error=error)
