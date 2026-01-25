"""MindsDB Service - HTTP API Client"""
import httpx
import json
import time
from typing import Optional, Dict, Any, List, Tuple
import os


class MindsDBService:
    """Service for interacting with MindsDB HTTP SQL API"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("MINDSDB_URL", "http://127.0.0.1:47334")
        self.api_endpoint = f"{self.base_url}/api/sql/query"
        self.timeout = 120.0
    
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute SQL query via MindsDB HTTP API"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_endpoint,
                    headers={"Content-Type": "application/json"},
                    json={"query": query}
                )
                result = response.json()
                execution_time = time.time() - start_time
                
                if result.get("type") == "error":
                    return {
                        "type": "error",
                        "columns": [],
                        "data": [],
                        "row_count": 0,
                        "error": result.get("error_message", "Unknown error"),
                        "execution_time": execution_time
                    }
                elif result.get("type") == "table":
                    return {
                        "type": "table",
                        "columns": result.get("column_names", []),
                        "data": result.get("data", []),
                        "row_count": len(result.get("data", [])),
                        "error": None,
                        "execution_time": execution_time
                    }
                else:
                    return {
                        "type": "ok",
                        "columns": [],
                        "data": [],
                        "row_count": 0,
                        "error": None,
                        "execution_time": execution_time
                    }
        except httpx.TimeoutException:
            return {
                "type": "error",
                "columns": [],
                "data": [],
                "row_count": 0,
                "error": "Query timeout - operation may still be running",
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "type": "error",
                "columns": [],
                "data": [],
                "row_count": 0,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def check_connection(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check if MindsDB server is accessible"""
        try:
            result = await self.execute_query("SELECT VERSION()")
            if result["type"] == "error":
                return False, None, result["error"]
            
            version = result["data"][0][0] if result["data"] else "Unknown"
            return True, version, None
        except Exception as e:
            return False, None, str(e)
    
    async def get_databases(self) -> List[Dict[str, Any]]:
        """Get list of databases (data sources)"""
        result = await self.execute_query("SHOW DATABASES")
        if result["type"] != "table":
            return []
        
        databases = []
        for row in result["data"]:
            db_name = row[0] if row else ""
            # Skip internal databases
            if db_name not in ["mindsdb", "information_schema", "files", "log"]:
                databases.append({
                    "name": db_name,
                    "engine": row[1] if len(row) > 1 else "unknown",
                    "tables": []
                })
        return databases
    
    async def get_tables(self, database: str) -> List[str]:
        """Get list of tables in a database"""
        result = await self.execute_query(f"SHOW TABLES FROM {database}")
        if result["type"] != "table":
            return []
        return [row[0] for row in result["data"] if row]
    
    async def get_table_schema(self, database: str, table: str) -> List[Dict[str, Any]]:
        """Get table schema/columns"""
        result = await self.execute_query(f"DESCRIBE {database}.{table}")
        if result["type"] != "table":
            return []
        
        columns = []
        for row in result["data"]:
            columns.append({
                "name": row[0] if row else "",
                "type": row[1] if len(row) > 1 else "unknown",
                "nullable": row[2] if len(row) > 2 else None,
                "key": row[3] if len(row) > 3 else None
            })
        return columns
    
    async def sample_data(self, database: str, table: str, limit: int = 10) -> Dict[str, Any]:
        """Get sample data from a table"""
        query = f"SELECT * FROM {database}.{table} LIMIT {limit}"
        return await self.execute_query(query)
    
    async def create_database(self, name: str, engine: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new database connection (data source)"""
        # Build parameters string
        params_str = json.dumps(parameters)
        
        query = f"""
        CREATE DATABASE {name}
        WITH ENGINE = '{engine}',
        PARAMETERS = {params_str}
        """
        return await self.execute_query(query.strip())
    
    async def drop_database(self, name: str) -> Dict[str, Any]:
        """Drop a database connection"""
        query = f"DROP DATABASE IF EXISTS {name}"
        return await self.execute_query(query)
    
    async def create_materialized_table(
        self, 
        table_name: str, 
        source_database: str, 
        source_table: str,
        columns: List[str] = None,
        where_clause: str = None,
        limit: int = None
    ) -> Dict[str, Any]:
        """Create a materialized table from source"""
        cols = ", ".join(columns) if columns else "*"
        query = f"CREATE TABLE mindsdb.{table_name} AS SELECT {cols} FROM {source_database}.{source_table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        if limit:
            query += f" LIMIT {limit}"
        
        return await self.execute_query(query)
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get list of ML models"""
        result = await self.execute_query("SHOW MODELS")
        if result["type"] != "table":
            return []
        
        models = []
        columns = result["columns"]
        for row in result["data"]:
            model_data = dict(zip(columns, row))
            models.append({
                "name": model_data.get("NAME", model_data.get("name", "")),
                "status": model_data.get("STATUS", model_data.get("status", "")),
                "predict": model_data.get("PREDICT", model_data.get("predict", "")),
                "engine": model_data.get("ENGINE", model_data.get("engine", ""))
            })
        return models
    
    async def get_jobs(self) -> List[Dict[str, Any]]:
        """Get list of jobs"""
        result = await self.execute_query("SHOW JOBS")
        if result["type"] != "table":
            return []
        
        jobs = []
        columns = result["columns"]
        for row in result["data"]:
            job_data = dict(zip(columns, row))
            jobs.append({
                "name": job_data.get("NAME", job_data.get("name", "")),
                "schedule": job_data.get("SCHEDULE", job_data.get("schedule", "")),
                "next_run": job_data.get("NEXT_RUN", job_data.get("next_run", ""))
            })
        return jobs
    
    async def get_knowledge_bases(self) -> List[Dict[str, Any]]:
        """Get list of knowledge bases"""
        result = await self.execute_query("SHOW KNOWLEDGE_BASES")
        if result["type"] != "table":
            return []
        
        kbs = []
        columns = result["columns"]
        for row in result["data"]:
            kb_data = dict(zip(columns, row))
            kbs.append({
                "name": kb_data.get("NAME", kb_data.get("name", "")),
                "model": kb_data.get("MODEL", kb_data.get("model", ""))
            })
        return kbs


# Singleton instance
mindsdb_service = MindsDBService()
