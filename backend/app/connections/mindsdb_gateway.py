"""MindsDB Service - HTTP API Client"""
import httpx
import json
import time
from typing import Optional, Dict, Any, List, Tuple
import os
import re


_CONNECTOR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,127}$")
_ENGINE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def _safe_connector_name(value: str) -> str:
    if not isinstance(value, str) or not _CONNECTOR_NAME.fullmatch(value):
        raise ValueError("invalid database name")
    return value


def _safe_engine_name(value: str) -> str:
    if not isinstance(value, str) or not _ENGINE_NAME.fullmatch(value):
        raise ValueError("invalid engine name")
    return value


def _quote_identifier(value: str, field: str) -> str:
    """실제 DB/table 이름은 제한하지 않고 backtick escaping으로 안전하게 인용한다."""
    if not isinstance(value, str) or not value or len(value) > 255 or any(ord(ch) < 32 for ch in value):
        raise ValueError(f"invalid {field}")
    return f"`{value.replace('`', '``')}`"


class MindsDBService:
    """Service for interacting with MindsDB HTTP SQL API"""
    
    def __init__(self, base_url: str = None):
        self._fixed_base_url = base_url
        self.timeout = 120.0
    
    @property
    def base_url(self) -> str:
        """Get base URL, reading from environment at call time"""
        if self._fixed_base_url:
            return self._fixed_base_url
        elif os.getenv("MINDSDB_URL"):
            return os.getenv("MINDSDB_URL")
        else:
            host = os.getenv("MINDSDB_HOST", "127.0.0.1")
            port = os.getenv("MINDSDB_API_PORT", "47334")
            return f"http://{host}:{port}"
    
    @property
    def api_endpoint(self) -> str:
        """Get API endpoint"""
        return f"{self.base_url}/api/sql/query"
    
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute SQL query via MindsDB HTTP API"""
        import logging
        logger = logging.getLogger(__name__)
        
        start_time = time.time()
        logger.debug("MindsDB query request", extra={"endpoint": self.api_endpoint})
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_endpoint,
                    headers={"Content-Type": "application/json"},
                    json={"query": query}
                )
                logger.info(f"MindsDB response status: {response.status_code}")
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
        database = _quote_identifier(database, "database name")
        result = await self.execute_query(f"SHOW TABLES FROM {database}")
        if result["type"] != "table":
            return []
        return [row[0] for row in result["data"] if row]
    
    async def get_table_schema(self, database: str, table: str) -> List[Dict[str, Any]]:
        """Get table schema/columns"""
        database = _quote_identifier(database, "database name")
        table = _quote_identifier(table, "table name")
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
        database = _quote_identifier(database, "database name")
        table = _quote_identifier(table, "table name")
        limit = max(1, min(int(limit), 1000))
        query = f"SELECT * FROM {database}.{table} LIMIT {limit}"
        return await self.execute_query(query)
    
    async def create_database(self, name: str, engine: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new database connection (data source) via REST API using sync requests"""
        import logging
        import requests
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        logger = logging.getLogger(__name__)
        _safe_connector_name(name)
        _safe_engine_name(engine)
        
        # Use REST API with sync requests (httpx has issues in uvicorn context)
        api_url = f"{self.base_url}/api/databases/"
        
        payload = {
            "database": {
                "name": name,
                "engine": engine,
                "parameters": parameters
            }
        }
        
        logger.info("Creating MindsDB database", extra={"api_url": api_url, "database": name})
        
        def sync_request():
            return requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
        
        try:
            # Run sync request in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                response = await loop.run_in_executor(pool, sync_request)
            
            logger.info("MindsDB database response", extra={"status_code": response.status_code, "database": name})
            
            if response.status_code in [200, 201]:
                return {
                    "type": "ok",
                    "columns": [],
                    "data": [],
                    "row_count": 0,
                    "error": None,
                    "execution_time": 0
                }
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("detail", error_data.get("title", response.text))
                return {
                    "type": "error",
                    "columns": [],
                    "data": [],
                    "row_count": 0,
                    "error": error_msg,
                    "execution_time": 0
                }
        except Exception as e:
            logger.error("MindsDB database request failed", extra={"database": name, "error_type": type(e).__name__})
            return {
                "type": "error",
                "columns": [],
                "data": [],
                "row_count": 0,
                "error": str(e),
                "execution_time": 0
            }
    
    async def drop_database(self, name: str) -> Dict[str, Any]:
        """Drop a database connection"""
        name = _safe_connector_name(name)
        query = f"DROP DATABASE IF EXISTS {_quote_identifier(name, 'database name')}"
        return await self.execute_query(query)

    async def inspect_database(self, name: str) -> Dict[str, Any]:
        """등록 여부가 아니라 대상 DB가 직접 실행한 native SELECT로 연결을 확인한다."""
        name = _safe_connector_name(name)
        connector = _quote_identifier(name, "database name")
        result = await self.execute_query(
            f"SELECT * FROM {connector} (SELECT 1 AS robo_connection_probe)"
        )
        return {
            "success": result["type"] == "table" and result["data"] == [[1]],
            "table_count": 0,
        }


# Singleton instance
mindsdb_gateway = MindsDBService()
