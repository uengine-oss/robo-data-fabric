"""MindsDB SQL 실행과 상태 확인 HTTP 경계."""

from fastapi import APIRouter

from ..connections.mindsdb_gateway import mindsdb_gateway
from ..contracts.query_api import MindsDBStatus, QueryRequest, QueryResponse


router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """MindsDB를 통해 대상 데이터소스 SQL을 실행한다."""
    result = await mindsdb_gateway.execute_query(request.query)
    return QueryResponse(**result)


@router.get("/status", response_model=MindsDBStatus)
async def get_status():
    """MindsDB 연결 상태를 반환한다."""
    connected, version, error = await mindsdb_gateway.check_connection()
    return MindsDBStatus(connected=connected, version=version, error=error)
