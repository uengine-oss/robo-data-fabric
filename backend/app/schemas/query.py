"""Query schemas for MindsDB UI"""
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


class MaterializedTableCreate(BaseModel):
    """Request schema for creating a materialized table"""
    table_name: str = Field(..., description="Name of the new table")
    source_database: str = Field(..., description="Source database name")
    source_table: str = Field(..., description="Source table name")
    columns: List[str] = Field(default=["*"], description="Columns to include")
    where_clause: Optional[str] = Field(None, description="Optional WHERE clause")
    limit: Optional[int] = Field(None, description="Optional LIMIT")
    
    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "cached_data",
                "source_database": "mysql_demo",
                "source_table": "home_rentals",
                "columns": ["*"],
                "limit": 1000
            }
        }


class ModelInfo(BaseModel):
    """Model information schema"""
    name: str
    status: str
    predict: Optional[str] = None
    engine: Optional[str] = None


class JobInfo(BaseModel):
    """Job information schema"""
    name: str
    schedule: Optional[str] = None
    next_run: Optional[str] = None


class KnowledgeBaseInfo(BaseModel):
    """Knowledge Base information schema"""
    name: str
    model: Optional[str] = None


class MindsDBStatus(BaseModel):
    """MindsDB server status"""
    connected: bool
    version: Optional[str] = None
    error: Optional[str] = None
