"""MindsDB SQL 실행과 상태 확인 HTTP 경계."""

from fastapi import APIRouter, HTTPException

from ..connections.mindsdb_gateway import mindsdb_gateway
from ..contracts.query_api import MindsDBStatus, QueryRequest, QueryResponse
from ..queries.read_only_sql import ReadOnlyQueryError, build_mindsdb_read_query


router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """MindsDB를 통해 대상 데이터소스 SQL을 실행한다."""
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
