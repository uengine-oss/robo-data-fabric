"""`CREATE DATASOURCE` 문장을 어떻게 짓는가.

⚠ 이 검사가 없어서 **기본 경로가 두 번 막힌 채로 납품판까지 갔다.** 둘 다
화면의 Schema 칸을 비우는 쪽 — 즉 **안내가 권하던 쪽**이었다.

    ① 빈 문자열이 그대로 가서 엔진이 거절했다
       ERROR: zero-length delimited identifier at or near ""
    ② 그걸 털고 나니 이번엔 **표가 하나도 안 들어왔다 — 조용히**
       엔진은 schema 가 없으면 IMPORT 를 건너뛴다(tables: 0)

계약 검사들은 게이트웨이를 **가짜로** 두고 있어서 문장 자체는 아무도 안 봤다.
"""
import pytest

from fabric.gateway import FabricGateway


class _Spy(FabricGateway):
    """문장과 파라미터만 받아 적는다 — Bolt 에 나가지 않는다."""

    def __init__(self) -> None:
        super().__init__()
        self.statement: str | None = None
        self.params: dict | None = None

    async def _datasource_names(self):
        return []

    async def execute_query(self, statement, parameters=None, **_):
        self.statement = statement
        self.params = dict(parameters or {})
        return {"type": "ok", "data": [], "columns": []}


@pytest.mark.asyncio
async def test_postgres_는_스키마를_비우면_public_을_넣는다():
    """비우는 것이 **보통의 길**이다. 그 길에서 표가 0개면 아무도 모른다."""
    spy = _Spy()
    result = await spy.create_database(
        "src1", "postgres",
        {"host": "10.0.0.5", "port": 5432, "database": "srctest",
         "user": "ro", "password": "x", "schema": "   "},
    )

    assert result["type"] == "ok"
    assert spy.params["schema"] == "public"
    # 나머지는 그대로 가야 한다 — 채우는 것과 바꾸는 것은 다르다.
    assert spy.params["host"] == "10.0.0.5"
    assert spy.params["database"] == "srctest"


@pytest.mark.asyncio
async def test_사람이_적은_스키마는_건드리지_않는다():
    spy = _Spy()
    await spy.create_database(
        "src2", "postgresql",
        {"host": "10.0.0.5", "database": "d", "user": "u", "schema": "sales"},
    )
    assert spy.params["schema"] == "sales"


@pytest.mark.asyncio
async def test_mysql_계열은_schema_를_채우지_않는다():
    """엔진이 MySQL 에서는 `database` 를 범위로 쓴다. 여기에 public 을 넣으면
    **없는 스키마를 가리키게** 된다."""
    spy = _Spy()
    await spy.create_database(
        "src3", "mysql",
        {"host": "10.0.0.5", "database": "shop", "user": "u", "schema": ""},
    )
    assert "schema" not in spy.params
    assert "schema" not in spy.statement
    assert spy.params["database"] == "shop"


@pytest.mark.asyncio
async def test_뜻이_있는_거짓값은_살린다():
    """`0`·`False` 는 비어 있는 것이 아니다. 같이 털면 설정이 조용히 바뀐다."""
    spy = _Spy()
    await spy.create_database(
        "src4", "mysql",
        {"host": "10.0.0.5", "port": 0, "ssl": False, "database": "shop"},
    )
    assert spy.params["port"] == 0
    assert spy.params["ssl"] is False


@pytest.mark.asyncio
async def test_비밀번호는_문장에_안_남는다():
    """값은 전부 Bolt 파라미터로 간다 — 질의문에 비밀번호가 없어야 한다."""
    spy = _Spy()
    await spy.create_database(
        "src5", "postgres",
        {"host": "10.0.0.5", "database": "d", "user": "u",
         "password": "s3cr3t-value", "schema": ""},
    )
    assert "s3cr3t-value" not in spy.statement
    assert spy.params["password"] == "s3cr3t-value"
