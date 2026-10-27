import asyncio
import unittest

from fastapi import HTTPException
import api.datasources as endpoints
from contracts.datasources import DataSourceCreate
from api.datasources import TestConnectionRequest


class _FabricFake:
    def __init__(
        self,
        inspection_success: bool = True,
        inspection_error: Exception | None = None,
        create_type: str | list[str] = "ok",
        create_status: int | list[int | None] | None = None,
        drop_type: str = "ok",
    ) -> None:
        self.created: list[tuple[str, str, dict]] = []
        self.dropped: list[str] = []
        self.inspection_success = inspection_success
        self.inspection_error = inspection_error
        self.create_type = create_type
        # ⚠ 409 = "그 이름이 이미 있다". 고아 복구가 이 신호로 돈다(ISS-61).
        self.create_status = create_status
        self.drop_type = drop_type

    async def create_database(self, name: str, engine: str, parameters: dict):
        self.created.append((name, engine, parameters))
        result_type = (
            self.create_type.pop(0)
            if isinstance(self.create_type, list)
            else self.create_type
        )
        status = (
            self.create_status.pop(0)
            if isinstance(self.create_status, list)
            else self.create_status
        )
        return {"type": result_type, "status_code": status}

    async def drop_database(self, name: str):
        self.dropped.append(name)
        return {"type": self.drop_type}

    async def inspect_database(self, name: str):
        if self.inspection_error is not None:
            raise self.inspection_error
        return {"success": self.inspection_success, "table_count": 0}


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
        return {"name": kwargs["name"], "engine": kwargs["engine"]}


async def test_create_keeps_credentials_out_of_registry_boundary() -> None:
    fabric, registry = _FabricFake(), _RegistryFake()
    originals = endpoints.fabric_gateway, endpoints.datasource_registry
    endpoints.fabric_gateway, endpoints.datasource_registry = fabric, registry
    try:
        result = await endpoints.create_datasource(
            DataSourceCreate(name="orders", engine="postgres", parameters={"host": "db", "user": "app", "password": "secret", "api_key": "token"}),
        )
    finally:
        endpoints.fabric_gateway, endpoints.datasource_registry = originals
    assert result == {"name": "orders", "engine": "postgres"}
    assert registry.parameters == {"host": "db", "user": "app"}
    assert fabric.created[0][2]["password"] == "secret" and "api_key" in fabric.created[0][2]


async def test_create_compensates_fabric_when_registry_fails() -> None:
    fabric, registry = _FabricFake(), _RegistryFake(fail_create=True)
    originals = endpoints.fabric_gateway, endpoints.datasource_registry
    endpoints.fabric_gateway, endpoints.datasource_registry = fabric, registry
    try:
        try:
            await endpoints.create_datasource(DataSourceCreate(name="orders", engine="postgres", parameters={"password": "secret"}))
        except HTTPException as exc:
            assert exc.status_code == 500
        else:
            raise AssertionError("registry failure must be surfaced")
    finally:
        endpoints.fabric_gateway, endpoints.datasource_registry = originals
    assert fabric.dropped == ["orders"]


async def test_create_rejects_registered_but_unreachable_target() -> None:
    fabric, registry = _FabricFake(inspection_success=False), _RegistryFake()
    originals = endpoints.fabric_gateway, endpoints.datasource_registry
    endpoints.fabric_gateway, endpoints.datasource_registry = fabric, registry
    try:
        with unittest.TestCase().assertRaises(HTTPException) as raised:
            await endpoints.create_datasource(
                DataSourceCreate(name="orders", engine="postgres", parameters={"host": "invalid"}),
            )
    finally:
        endpoints.fabric_gateway, endpoints.datasource_registry = originals
    assert raised.exception.status_code == 400
    assert fabric.dropped == ["orders"]
    assert registry.parameters is None


async def test_create_compensates_when_target_inspection_raises() -> None:
    fabric, registry = _FabricFake(inspection_error=TimeoutError("target timeout")), _RegistryFake()
    originals = endpoints.fabric_gateway, endpoints.datasource_registry
    endpoints.fabric_gateway, endpoints.datasource_registry = fabric, registry
    try:
        with unittest.TestCase().assertRaises(HTTPException) as raised:
            await endpoints.create_datasource(
                DataSourceCreate(name="orders", engine="postgres", parameters={"host": "slow"}),
            )
    finally:
        endpoints.fabric_gateway, endpoints.datasource_registry = originals
    assert raised.exception.status_code == 400
    assert fabric.dropped == ["orders"]
    assert registry.parameters is None


async def test_create_repairs_orphan_fabric_connector() -> None:
    # 첫 시도는 **이름이 겹쳐서** 실패한다 — 그래서 409 다.
    fabric = _FabricFake(create_type=["error", "ok"], create_status=[409, None])
    registry = _RegistryFake()
    originals = endpoints.fabric_gateway, endpoints.datasource_registry
    endpoints.fabric_gateway, endpoints.datasource_registry = fabric, registry
    try:
        result = await endpoints.create_datasource(
            DataSourceCreate(
                name="orders",
                engine="postgres",
                parameters={"host": "db", "password": "secret"},
            ),
        )
    finally:
        endpoints.fabric_gateway, endpoints.datasource_registry = originals
    assert result["name"] == "orders"
    assert fabric.dropped == ["orders"]
    assert len(fabric.created) == 2


async def test_connection_probe_checks_target_and_always_cleans_up() -> None:
    fabric = _FabricFake(inspection_success=False)
    original = endpoints.fabric_gateway
    endpoints.fabric_gateway = fabric
    try:
        result = await endpoints.test_connection_params(
            TestConnectionRequest(engine="postgres", host="invalid", port=1)
        )
    finally:
        endpoints.fabric_gateway = original
    assert result["success"] is False
    assert len(fabric.created) == 1
    assert fabric.dropped == [fabric.created[0][0]]


async def test_failed_probe_creation_does_not_emit_false_cleanup_failure() -> None:
    fabric = _FabricFake(create_type="error")
    original = endpoints.fabric_gateway
    endpoints.fabric_gateway = fabric
    try:
        result = await endpoints.test_connection_params(
            TestConnectionRequest(engine="postgres", host="invalid", port=1)
        )
    finally:
        endpoints.fabric_gateway = original
    assert result["success"] is False
    assert fabric.dropped == []


async def test_probe_cleanup_failure_is_not_reported_as_success() -> None:
    fabric = _FabricFake(drop_type="error")
    original = endpoints.fabric_gateway
    endpoints.fabric_gateway = fabric
    try:
        with unittest.TestCase().assertRaises(HTTPException) as raised:
            await endpoints.test_connection_params(
                TestConnectionRequest(engine="postgres", host="db", port=5432)
            )
    finally:
        endpoints.fabric_gateway = original
    assert raised.exception.status_code == 502


class DataSourceCreationTest(unittest.IsolatedAsyncioTestCase):
    async def test_credentials_stop_at_registry_boundary(self) -> None:
        await test_create_keeps_credentials_out_of_registry_boundary()

    async def test_registry_failure_is_compensated(self) -> None:
        await test_create_compensates_fabric_when_registry_fails()

    async def test_unreachable_target_is_rejected_before_registry(self) -> None:
        await test_create_rejects_registered_but_unreachable_target()

    async def test_target_inspection_exception_is_compensated(self) -> None:
        await test_create_compensates_when_target_inspection_raises()

    async def test_orphan_connector_is_repaired(self) -> None:
        await test_create_repairs_orphan_fabric_connector()

    async def test_probe_requires_real_target_access_and_cleanup(self) -> None:
        await test_connection_probe_checks_target_and_always_cleans_up()

    async def test_failed_probe_creation_requires_no_cleanup(self) -> None:
        await test_failed_probe_creation_does_not_emit_false_cleanup_failure()

    async def test_probe_cleanup_failure_is_explicit(self) -> None:
        await test_probe_cleanup_failure_is_not_reported_as_success()


if __name__ == "__main__":
    asyncio.run(test_create_keeps_credentials_out_of_registry_boundary())
    asyncio.run(test_create_compensates_fabric_when_registry_fails())
    print("[OK] datasource creation saga")
