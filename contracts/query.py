"""Public read-only query and MindsDB status contracts."""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


class QueryRequest(BaseModel):
    """대상 datasource에서 실행할 bounded read-only SQL."""
    datasource: str = Field(
        ..., min_length=1, max_length=128, pattern=r"^[A-Za-z_][A-Za-z0-9_-]*$"
    )
    query: str = Field(..., min_length=1, max_length=100_000)
    max_rows: int = Field(default=100, ge=1, le=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "datasource": "shopmall",
                "query": "SELECT * FROM public.orders",
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


class MindsDBStatus(BaseModel):
    """MindsDB server status"""
    connected: bool
    version: Optional[str] = None
    error: Optional[str] = None
