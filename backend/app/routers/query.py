"""Query Router"""
from fastapi import APIRouter, HTTPException
from ..schemas.query import (
    QueryRequest, 
    QueryResponse, 
    MaterializedTableCreate,
    ModelInfo,
    JobInfo,
    KnowledgeBaseInfo,
    MindsDBStatus
)
from ..services.mindsdb_service import mindsdb_service
from typing import List

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """Execute SQL query on MindsDB"""
    result = await mindsdb_service.execute_query(request.query)
    return QueryResponse(**result)


@router.get("/status", response_model=MindsDBStatus)
async def get_status():
    """Check MindsDB server status"""
    connected, version, error = await mindsdb_service.check_connection()
    return MindsDBStatus(connected=connected, version=version, error=error)


@router.post("/materialized-table")
async def create_materialized_table(request: MaterializedTableCreate):
    """Create a materialized table from source data"""
    result = await mindsdb_service.create_materialized_table(
        table_name=request.table_name,
        source_database=request.source_database,
        source_table=request.source_table,
        columns=request.columns,
        where_clause=request.where_clause,
        limit=request.limit
    )
    
    if result["type"] == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {"message": f"Materialized table '{request.table_name}' created successfully"}


@router.get("/models", response_model=List[ModelInfo])
async def get_models():
    """Get list of ML models"""
    models = await mindsdb_service.get_models()
    return models


@router.get("/jobs", response_model=List[JobInfo])
async def get_jobs():
    """Get list of scheduled jobs"""
    jobs = await mindsdb_service.get_jobs()
    return jobs


@router.get("/knowledge-bases", response_model=List[KnowledgeBaseInfo])
async def get_knowledge_bases():
    """Get list of knowledge bases"""
    kbs = await mindsdb_service.get_knowledge_bases()
    return kbs
