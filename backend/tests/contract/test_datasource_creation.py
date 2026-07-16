import asyncio
import unittest

from fastapi import HTTPException
from starlette.requests import Request

import app.http.datasource_endpoints as endpoints
from app.contracts.datasource_api import DataSourceCreate


class _MindsDBFake:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, dict]] = []
        self.dropped: list[str] = []

    async def create_database(self, name: str, engine: str, parameters: dict):
        self.created.append((name, engine, parameters))
        return {"type": "ok"}

    async def drop_database(self, name: str):
        self.dropped.append(name)
        return {"type": "ok"}


class _RegistryFake:
    def __init__(self, fail_create: bool = False) -> None:
        self.fail_create = fail_create
        self.parameters: dict | None = None

    async def get_datasource(self, name: str):
        return None

    async def create_datasource(self, **kwargs):
        self.parameters = kwargs["parameters"]
        if self.fail_create:
            raise RuntimeError("registry unavailable")
        return {"datasource_id": "ds-1", "graph_owner": "data-fabric", "workspace_id": kwargs["workspace_id"], "name": kwargs["name"], "engine": kwargs["engine"]}


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [(b"x-workspace-id", b"ws-1")]})


async def test_create_keeps_credentials_out_of_registry_boundary() -> None:
    mindsdb, registry = _MindsDBFake(), _RegistryFake()
    originals = endpoints.mindsdb_gateway, endpoints.datasource_registry
    endpoints.mindsdb_gateway, endpoints.datasource_registry = mindsdb, registry
    try:
        result = await endpoints.create_datasource(
            DataSourceCreate(name="orders", engine="postgres", parameters={"host": "db", "user": "app", "password": "secret", "api_key": "token"}),
            _request(),
        )
    finally:
        endpoints.mindsdb_gateway, endpoints.datasource_registry = originals
    assert result["workspace_id"] == "ws-1"
    assert registry.parameters == {"host": "db", "user": "app"}
    assert mindsdb.created[0][2]["password"] == "secret" and "api_key" in mindsdb.created[0][2]


async def test_create_compensates_mindsdb_when_registry_fails() -> None:
    mindsdb, registry = _MindsDBFake(), _RegistryFake(fail_create=True)
    originals = endpoints.mindsdb_gateway, endpoints.datasource_registry
    endpoints.mindsdb_gateway, endpoints.datasource_registry = mindsdb, registry
    try:
        try:
            await endpoints.create_datasource(DataSourceCreate(name="orders", engine="postgres", parameters={"password": "secret"}), _request())
        except HTTPException as exc:
            assert exc.status_code == 500
        else:
            raise AssertionError("registry failure must be surfaced")
    finally:
        endpoints.mindsdb_gateway, endpoints.datasource_registry = originals
    assert mindsdb.dropped == ["orders"]


class DataSourceCreationTest(unittest.IsolatedAsyncioTestCase):
    async def test_credentials_stop_at_registry_boundary(self) -> None:
        await test_create_keeps_credentials_out_of_registry_boundary()

    async def test_registry_failure_is_compensated(self) -> None:
        await test_create_compensates_mindsdb_when_registry_fails()


if __name__ == "__main__":
    asyncio.run(test_create_keeps_credentials_out_of_registry_boundary())
    asyncio.run(test_create_compensates_mindsdb_when_registry_fails())
    print("[OK] datasource creation saga")
