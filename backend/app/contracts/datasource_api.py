"""Public DataSource request and response contracts."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=128,
        pattern=r"^[A-Za-z_][A-Za-z0-9_-]*$",
        description="Stable connection name",
    )
    engine: str = Field(
        ..., min_length=1, pattern=r"^[A-Za-z_][A-Za-z0-9_-]*$",
        description="MindsDB engine name",
    )
    parameters: dict[str, Any] = Field(default_factory=dict, description="Ephemeral connection parameters")


class DataSourceResponse(BaseModel):
    name: str
    engine: str
    datasource_id: Optional[str] = None
    graph_owner: Optional[str] = None
    workspace_id: Optional[str] = None
    display_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None
    created_at: Optional[str] = None
    tables: list[str] = Field(default_factory=list)


class DataSourceList(BaseModel):
    datasources: list[DataSourceResponse]
