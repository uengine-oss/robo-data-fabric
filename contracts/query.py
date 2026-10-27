"""읽기 전용 질의와 패브릭 상태 계약.

⚠ 2026-10-27: `query` 는 이제 **사이퍼**다(SQL 이 아니다). 이 엔진은 임의 SQL 을
   일부러 받지 않는다 — SQL 은 가상 노드 정의(`AS SELECT`) 안에만 둔다(ADR-029).
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


class QueryRequest(BaseModel):
    """경계 있는 읽기 전용 **사이퍼**.

    `datasource` 는 "등록된 것인지" 를 보는 자리다. 질의 자체는 graph 에 대고
    돌고, 그 graph 안에서 가상 노드가 원천 행을 대신한다.
    """
    datasource: str = Field(
        ..., min_length=1, max_length=128, pattern=r"^[A-Za-z_][A-Za-z0-9_-]*$"
    )
    query: str = Field(..., min_length=1, max_length=100_000)
    max_rows: int = Field(default=100, ge=1, le=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "datasource": "shopmall",
                "query": "MATCH (o:Order) RETURN o.id, o.total",
                "max_rows": 100,
            }
        }


class QueryResponse(BaseModel):
    """Response schema for query execution"""
    type: str  # "table" or "ok" or "error"
    columns: List[str] = Field(default_factory=list)
    data: List[List[Any]] = Field(default_factory=list)
    row_count: int = 0
    error: Optional[str] = None
    execution_time: Optional[float] = None


class FabricStatus(BaseModel):
    """패브릭(그래프 엔진) 상태"""
    connected: bool
    version: Optional[str] = None
    error: Optional[str] = None
