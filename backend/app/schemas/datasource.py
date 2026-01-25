"""Data source schemas for MindsDB UI"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class DataSourceType(str, Enum):
    """Supported data source types"""
    MYSQL = "mysql"
    POSTGRES = "postgres"
    NEO4J = "neo4j"
    WEB = "web"
    OPENAI = "minds_endpoint"
    MONGODB = "mongodb"
    REDIS = "redis"
    ELASTICSEARCH = "elasticsearch"


class DataSourceCreate(BaseModel):
    """Request schema for creating a data source"""
    name: str = Field(..., description="Name of the data source connection")
    engine: DataSourceType = Field(..., description="Type of data source engine")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Connection parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "my_mysql_db",
                "engine": "mysql",
                "parameters": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "password",
                    "database": "mydb"
                }
            }
        }


class DataSourceResponse(BaseModel):
    """Response schema for data source"""
    name: str
    engine: str
    tables: List[str] = []


class DataSourceList(BaseModel):
    """Response schema for list of data sources"""
    datasources: List[DataSourceResponse]


class TableInfo(BaseModel):
    """Table information schema"""
    name: str
    columns: List[Dict[str, Any]] = []


class TableData(BaseModel):
    """Table data schema"""
    columns: List[str]
    data: List[List[Any]]
    total_rows: int


# Data source type configurations
DATASOURCE_CONFIGS = {
    DataSourceType.MYSQL: {
        "display_name": "MySQL",
        "icon": "mysql",
        "fields": [
            {"name": "host", "label": "Host", "type": "text", "required": True, "default": "localhost"},
            {"name": "port", "label": "Port", "type": "number", "required": True, "default": 3306},
            {"name": "user", "label": "Username", "type": "text", "required": True},
            {"name": "password", "label": "Password", "type": "password", "required": True},
            {"name": "database", "label": "Database", "type": "text", "required": True},
            {"name": "datafabric_host", "label": "Data Fabric용 Host (선택)", "type": "text", "required": False, "placeholder": "예: host.docker.internal"},
            {"name": "datafabric_port", "label": "Data Fabric용 Port (선택)", "type": "number", "required": False, "placeholder": "기본값: 위 Port 사용"}
        ]
    },
    DataSourceType.POSTGRES: {
        "display_name": "PostgreSQL",
        "icon": "postgresql",
        "fields": [
            {"name": "host", "label": "Host", "type": "text", "required": True, "default": "localhost"},
            {"name": "port", "label": "Port", "type": "number", "required": True, "default": 5432},
            {"name": "user", "label": "Username", "type": "text", "required": True},
            {"name": "password", "label": "Password", "type": "password", "required": True},
            {"name": "database", "label": "Database", "type": "text", "required": True},
            {"name": "datafabric_host", "label": "Data Fabric용 Host (선택)", "type": "text", "required": False, "placeholder": "예: host.docker.internal"},
            {"name": "datafabric_port", "label": "Data Fabric용 Port (선택)", "type": "number", "required": False, "placeholder": "기본값: 위 Port 사용"}
        ]
    },
    DataSourceType.NEO4J: {
        "display_name": "Neo4j",
        "icon": "neo4j",
        "fields": [
            {"name": "host", "label": "Host", "type": "text", "required": True, "default": "localhost"},
            {"name": "port", "label": "Port", "type": "number", "required": True, "default": 7687},
            {"name": "user", "label": "Username", "type": "text", "required": True, "default": "neo4j"},
            {"name": "password", "label": "Password", "type": "password", "required": True}
        ]
    },
    DataSourceType.WEB: {
        "display_name": "Web Crawler",
        "icon": "web",
        "fields": []
    },
    DataSourceType.OPENAI: {
        "display_name": "OpenAI API",
        "icon": "openai",
        "fields": [
            {"name": "api_key", "label": "API Key", "type": "password", "required": True},
            {"name": "model_name", "label": "Model Name", "type": "text", "required": False, "default": "gpt-4o"}
        ]
    },
    DataSourceType.MONGODB: {
        "display_name": "MongoDB",
        "icon": "mongodb",
        "fields": [
            {"name": "host", "label": "Host", "type": "text", "required": True, "default": "localhost"},
            {"name": "port", "label": "Port", "type": "number", "required": True, "default": 27017},
            {"name": "username", "label": "Username", "type": "text", "required": False},
            {"name": "password", "label": "Password", "type": "password", "required": False},
            {"name": "database", "label": "Database", "type": "text", "required": True}
        ]
    },
    DataSourceType.REDIS: {
        "display_name": "Redis",
        "icon": "redis",
        "fields": [
            {"name": "host", "label": "Host", "type": "text", "required": True, "default": "localhost"},
            {"name": "port", "label": "Port", "type": "number", "required": True, "default": 6379},
            {"name": "password", "label": "Password", "type": "password", "required": False},
            {"name": "db", "label": "Database Index", "type": "number", "required": False, "default": 0}
        ]
    },
    DataSourceType.ELASTICSEARCH: {
        "display_name": "Elasticsearch",
        "icon": "elasticsearch",
        "fields": [
            {"name": "hosts", "label": "Hosts (comma-separated)", "type": "text", "required": True, "default": "localhost:9200"},
            {"name": "user", "label": "Username", "type": "text", "required": False},
            {"name": "password", "label": "Password", "type": "password", "required": False}
        ]
    }
}
