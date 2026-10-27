"""읽기 전용 사이퍼 실행과 상태 확인 HTTP 경계.

⚠ 2026-10-27 에 MindsDB SQL 통과에서 **사이퍼**로 옮겼다. 이 엔진은 임의 SQL 을
   Bolt 로 받지 않는다 — 여섯 방향으로 재서 전부 거절되는 것을 봤다(ADR-029 가
   일부러 닫았다: "SQL 은 노드 정의 안에만 둔다").
⚠ 그래서 **ISS-65 의 질의 화면은 사이퍼 화면**이 된다. SQL 화면으로 만들면 두 번
   만들게 된다.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.graph_connection import apply_neo4j_override
from contracts.query import FabricStatus, QueryRequest, QueryResponse
from fabric.gateway import fabric_gateway
from queries.policy import ReadOnlyQueryError, validate_read_only_cypher
from registry.datasources import datasource_registry


router = APIRouter(
    prefix="/query",
    tags=["Query"],
    dependencies=[Depends(apply_neo4j_override)],
)


@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """등록된 데이터소스의 graph 에 읽기 전용 사이퍼를 돌린다."""
    if not await datasource_registry.get_datasource(request.datasource):
        raise HTTPException(status_code=404, detail="DataSource not found")
    try:
        cypher = validate_read_only_cypher(request.query)
    except ReadOnlyQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = await fabric_gateway.execute_query(cypher)
    # ⚠ 경계는 **돌려줄 때** 지킨다. 사이퍼에 LIMIT 를 덧붙이면 사람이 쓴 ORDER BY
    #    나 집계의 뜻이 바뀐다 — 자르는 쪽이 정직하다. 자른 것은 말해 준다.
    if result["type"] == "table" and len(result["data"]) > request.max_rows:
        result["data"] = result["data"][: request.max_rows]
        result["row_count"] = len(result["data"])
        result["error"] = f"{request.max_rows}행까지만 보여 줍니다"
    return QueryResponse(**result)


@router.get("/status", response_model=FabricStatus)
async def get_status():
    """그래프 엔진이 패브릭 문장을 받는지 본다."""
    connected, version, error = await fabric_gateway.check_connection()
    return FabricStatus(connected=connected, version=version, error=error)
