"""`CREATE DATASOURCE` 문장을 어떻게 짓는가.

⚠ 이 검사가 없어서 **기본 경로가 막힌 채로 납품판까지 갔다.** 화면의 Schema
칸을 비우면(=안내가 권하는 쪽) 빈 문자열이 엔진까지 가서
`zero-length delimited identifier` 로 거절됐다. 계약 검사들은 게이트웨이를
가짜로 두고 있어서 **문장 자체는 아무도 안 보고 있었다.**
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
async def test_빈_값은_문장에서_빠진다():
    """Schema 를 비우는 것이 **보통의 길**이다. 빈 식별자를 만들면 안 된다."""
    spy = _Spy()
    result = await spy.create_database(
        "src1", "postgres",
        {"host": "10.0.0.5", "port": 5432, "database": "srctest",
         "user": "ro", "password": "x", "schema": "   "},
    )

    assert result["type"] == "ok"
    assert "schema" not in spy.statement
    assert "schema" not in spy.params
    # 나머지는 그대로 가야 한다 — 비우는 것과 지우는 것은 다르다.
    assert spy.params["host"] == "10.0.0.5"
    assert spy.params["database"] == "srctest"


@pytest.mark.asyncio
async def test_뜻이_있는_거짓값은_살린다():
    """`0`·`False` 는 비어 있는 것이 아니다. 같이 털면 설정이 조용히 바뀐다."""
    spy = _Spy()
    await spy.create_database(
        "src2", "postgres",
        {"host": "10.0.0.5", "port": 0, "ssl": False, "schema": "sales"},
    )

    assert spy.params["port"] == 0
    assert spy.params["ssl"] is False
    assert spy.params["schema"] == "sales"


@pytest.mark.asyncio
async def test_비밀번호는_문장에_안_남는다():
    """값은 전부 Bolt 파라미터로 간다 — 질의문에 비밀번호가 없어야 한다."""
    spy = _Spy()
    await spy.create_database(
        "src3", "postgres",
        {"host": "10.0.0.5", "password": "s3cr3t-value", "schema": ""},
    )

    assert "s3cr3t-value" not in spy.statement
    assert spy.params["password"] == "s3cr3t-value"
