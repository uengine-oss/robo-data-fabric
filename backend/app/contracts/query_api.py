"""Public MindsDB query and status contracts."""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


class QueryRequest(BaseModel):
    """Request schema for SQL query execution"""
    query: str = Field(..., description="SQL query to execute")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "SELECT * FROM information_schema.databases"
            }
        }


class QueryResponse(BaseModel):
    """Response schema for query execution"""
    type: str  # "table" or "ok" or "error"
    columns: List[str] = []
    data: List[List[Any]] = []
    row_count: int = 0
    error: Optional[str] = None
    execution_time: Optional[float] = None


class MindsDBStatus(BaseModel):
    """MindsDB server status"""
    connected: bool
    version: Optional[str] = None
    error: Optional[str] = None
