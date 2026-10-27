"""Ontological 의 virtual fabric 을 Bolt 로 쓰는 게이트웨이.

MindsDB 게이트웨이(`mindsdb/transport.py`)를 **같은 메서드 이름으로** 대신한다.
그래서 `api/datasources.py`·`api/tables.py`·`api/query.py` 는 부르는 이름을 안 바꾼다.

## 왜 Bolt 인가

패브릭 문장(`CREATE DATASOURCE`·`SHOW TABLES FROM`·`CREATE VIRTUAL NODE`…)은
`og_cypher()` 가 알아보므로 **사이퍼가 들어오는 곳이면 어디서나** 받는다. 즉 이
서비스가 이미 들고 있는 `neo4j` 드라이버로 보낼 수 있고, **새 의존이 하나도 없다**
(2026-10-27 실측: 동작 일곱을 이 경로로 전부 돌렸다). MindsDB 를 쓸 때는 HTTP
클라이언트와 그 제품 하나가 더 필요했다.

## 비밀번호

`PARAMETERS` 의 **값**은 파라미터로 보낸다(`password: $pw`) — 질의문에 안 남고,
엔진이 감사 기록에 설정 블록을 가려서 남긴다. 저장은 FDW user mapping 이 하고
그것은 superuser 만 읽는다. 즉 **우리 registry 는 여전히 비밀번호를 안 가진다**
(`credentials/allowlist.py` 가 코드로 강제하는 그 성질이 유지된다).

## ⚠ 이름은 문장에 박힌다

이 문법에는 따옴표가 없다. 그래서 모든 이름이 `fabric/statements.py` 를 지나야
한다 — 그 모듈이 유일한 문이다.

## ⚠ 컬럼·표본은 **임시 가상 노드**로 읽는다

패브릭 문장에 `SHOW COLUMNS` 가 없다(실측: `SHOW PROPERTIES OF`·`SHOW COLUMNS
FROM` 둘 다 문법 오류). 대신 가상 노드를 선언하면 `MATCH (x:T) RETURN x` 가
**속성 전부를 이름과 값으로** 준다. 그래서 선언 → 읽기 → **떼기** 로 왕복한다.
이 저장소가 `test-connection` 에서 이미 쓰는 `robo_probe_<uuid>` 와 같은 꼴이고,
그래서 그래프의 타입 목록에 **남는 것이 없다**.
⚠ 떼기가 실패하면 타입이 남는다 — 그때는 로그로 남기고 사람이 치울 수 있게 한다.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError
from neo4j.graph import Node

from fabric import statements as st
from registry.connection import get_override
from registry.driver import Neo4jConfig
from shared.config.settings import settings


logger = logging.getLogger(__name__)


def _result(
    result_type: str,
    *,
    columns: list[str] | None = None,
    data: list[list[Any]] | None = None,
    error: str | None = None,
    execution_time: float = 0.0,
    status_code: int | None = None,
) -> dict[str, Any]:
    """MindsDB 게이트웨이와 **같은 모양**을 돌려준다 — 화면 계약을 안 건드린다."""
    rows = data or []
    return {
        "type": result_type,
        "columns": columns or [],
        "data": rows,
        "row_count": len(rows),
        "error": error,
        "status_code": status_code,
        "execution_time": execution_time,
    }


class FabricGateway:
    """패브릭 문장을 Bolt 로 보낸다. 연결은 registry 와 **같은 규칙**으로 고른다."""

    def __init__(self, config: Neo4jConfig | None = None) -> None:
        self.config = config or Neo4jConfig(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        self._drivers: dict[tuple[str, str, str], Any] = {}

    # ── 연결 ───────────────────────────────────────────────────────────────
    def _resolve_config(self) -> Neo4jConfig:
        """요청이 실어 보낸 연결을 쓴다 — registry 와 같은 자리를 본다.

        ⚠ 이것을 registry 와 다르게 고르면 **등록은 한 graph 에, 조회는 다른
        graph 에** 가게 된다. 둘은 같은 contextvar 를 본다.
        """
        override = get_override()
        if override is None:
            return self.config
        return Neo4jConfig(
            uri=override.uri,
            user=override.user,
            password=override.password,
            database=override.database or self.config.database,
        )

    async def _driver(self, config: Neo4jConfig):
        key = (config.uri, config.user, config.password)
        driver = self._drivers.get(key)
        if driver is None:
            driver = AsyncGraphDatabase.driver(config.uri, auth=(config.user, config.password))
            self._drivers[key] = driver
        return driver

    async def close(self) -> None:
        for driver in self._drivers.values():
            await driver.close()
        self._drivers.clear()

    async def _run(self, statement: str, params: dict[str, Any] | None = None):
        """한 문장을 보내고 (키, 행) 을 돌려준다. 예외는 호출부가 받는다."""
        config = self._resolve_config()
        driver = await self._driver(config)
        async with driver.session(database=config.database) as session:
            result = await session.run(statement, params or {})
            # ⚠ `AsyncResult` 는 동기로 순회하지 못한다 — `async for` 다.
            records = [record async for record in result]
            keys = list(result.keys())
        return keys, records

    # ── 공개 면 (MindsDB 게이트웨이와 같은 이름) ──────────────────────────
    async def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """사이퍼(또는 패브릭 문장) 하나를 실행하고 모양을 맞춰 돌려준다.

        ⚠ `params` 는 **값**을 보내는 자리다. 비밀번호가 질의문에 남지 않는 이유가
        여기다 — 이름은 문장에 박히고(검사를 지난다) 값은 여기로 간다.
        """
        started = time.monotonic()
        try:
            keys, records = await self._run(query, params)
        except Neo4jError as exc:
            # ⚠ 엔진이 돌려준 말은 그대로 쓴다 — 거절의 이유가 거기 있다
            #   ("'Emp' is a virtual node type and read-only: its rows live in …").
            #   덮으면 ISS-60 에서 고친 것을 다시 망가뜨린다.
            logger.warning("Fabric statement rejected", extra={"code": exc.code})
            return _result(
                "error",
                error=str(exc.message or "질의가 거절되었습니다."),
                execution_time=time.monotonic() - started,
            )
        except Exception:
            logger.exception("Fabric transport failed")
            return _result(
                "error",
                error="그래프 연결에 실패했습니다.",
                execution_time=time.monotonic() - started,
            )
        elapsed = time.monotonic() - started
        if not keys:
            return _result("ok", execution_time=elapsed)
        return _result(
            "table",
            columns=keys,
            data=[[record.get(k) for k in keys] for record in records],
            execution_time=elapsed,
        )

    async def check_connection(self) -> tuple[bool, str | None, str | None]:
        """엔진이 패브릭 문장을 받는지 본다.

        ⚠ MindsDB 때는 `SELECT VERSION()` 으로 판 번호까지 받았다. 여기서는 판
        번호를 주는 문장이 없다 — 그래서 **없는 값을 지어내지 않고 None 을 준다**.
        """
        result = await self.execute_query("SHOW DATASOURCES")
        if result["type"] == "error":
            return False, None, result["error"]
        return True, None, None

    async def _datasource_names(self) -> list[str]:
        result = await self.execute_query("SHOW DATASOURCES")
        if result["type"] != "table":
            return []
        return [str(row[0]) for row in result["data"] if row]

    async def create_database(
        self, name: str, engine: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """데이터소스 하나를 등록한다.

        ⚠ 이름이 이미 있으면 **409 로 돌려준다.** 호출부(`api/datasources.py`)가
        "이름이 겹쳤다" 와 "접속값이 틀렸다" 를 갈라 말하는 근거이고, 고아 복구
        (ISS-61)가 그 신호로 돈다. 오류 문구를 글자로 맞추지 않고 **먼저 물어서**
        판단한다 — 문구는 판마다 바뀌지만 목록은 안 바뀐다.
        """
        try:
            ds = st.bare_name(name, "datasource name")
            eng = st.engine_name(engine)
        except ValueError as exc:
            return _result("error", error=str(exc), status_code=400)

        if ds in await self._datasource_names():
            return _result("error", error=f"datasource '{ds}' already exists", status_code=409)

        keys = sorted(parameters)
        assignments = ", ".join(f"{k}: ${k}" for k in keys)
        statement = (
            f"CREATE DATASOURCE {ds} WITH ENGINE = '{eng}', "
            f"PARAMETERS = {{{assignments}}}"
        )
        # ⚠ 값은 **전부 파라미터로** 간다 — 비밀번호가 질의문에 남지 않는다.
        result = await self.execute_query(statement, {k: parameters[k] for k in keys})
        if result["type"] == "error":
            return _result("error", error=result["error"], status_code=502)
        return _result("ok")

    async def drop_database(self, name: str) -> dict[str, Any]:
        """데이터소스를 떼어 낸다 — **가상 타입을 먼저 뗀다.**

        ⚠ 엔진이 순서를 강제한다(실측 2026-10-27):
        `datasource 'loop' still backs virtual types (…); drop or materialize them
        first`. MindsDB 때는 `DROP DATABASE` 하나로 끝났으므로 **여기가 바뀌는
        자리**다. 이 가드는 좋은 쪽이다 — ISS-61(고아 복구)이 생긴 까닭이 바로
        "한쪽만 남는 상태" 였고, 이것은 그 상태를 **애초에 못 만들게** 한다.
        """
        try:
            ds = st.bare_name(name, "datasource name")
        except ValueError as exc:
            return _result("error", error=str(exc), status_code=400)

        await self._drop_dependents(ds)
        return await self.execute_query(f"DROP DATASOURCE {ds}")

    async def _drop_dependents(self, ds: str) -> None:
        """이 데이터소스에 매달린 가상 관계와 가상 노드를 뗀다."""
        nodes = await self.execute_query("SHOW VIRTUAL NODES")
        mine: list[str] = []
        if nodes["type"] == "table":
            cols = {name: i for i, name in enumerate(nodes["columns"])}
            for row in nodes["data"]:
                source = str(row[cols.get("source", 1)] or "")
                if source.startswith(f"{ds}."):
                    mine.append(str(row[cols.get("node", 0)]))
        if not mine:
            return
        # 관계가 노드를 붙잡고 있으므로 관계를 먼저 뗀다.
        rels = await self.execute_query("SHOW VIRTUAL RELATIONSHIPS")
        if rels["type"] == "table":
            rcols = {name: i for i, name in enumerate(rels["columns"])}
            for row in rels["data"]:
                ends = f"{row[rcols.get('from', 1)]} {row[rcols.get('to', 2)]}"
                if any(f"{n}." in ends for n in mine):
                    name = str(row[rcols.get("relationship", 0)])
                    dropped = await self.execute_query(f"DROP VIRTUAL RELATIONSHIP {name}")
                    if dropped["type"] == "error":
                        logger.error("Virtual relationship drop failed",
                                     extra={"relationship": name, "datasource": ds})
        for node in mine:
            dropped = await self.execute_query(f"DROP VIRTUAL NODE {node}")
            if dropped["type"] == "error":
                logger.error("Virtual node drop failed",
                             extra={"virtual_node": node, "datasource": ds})

    async def inspect_database(self, name: str) -> dict[str, Any]:
        """연결이 실제로 원천에 닿는지 본다 — 표 목록을 받아 본다."""
        try:
            ds = st.bare_name(name, "datasource name")
        except ValueError:
            return {"success": False, "table_count": 0}
        result = await self.execute_query(f"SHOW TABLES FROM {ds}")
        if result["type"] != "table":
            return {"success": False, "table_count": 0}
        return {"success": True, "table_count": result["row_count"]}

    async def get_tables(self, database: str) -> list[str]:
        ds = st.bare_name(database, "datasource name")
        result = await self.execute_query(f"SHOW TABLES FROM {ds}")
        if result["type"] == "error":
            raise RuntimeError("fabric table listing failed")
        if result["type"] != "table":
            raise RuntimeError("fabric table listing returned no table result")
        prefix = f"{ds}."
        out = []
        for row in result["data"]:
            if not row:
                continue
            name = str(row[0])
            out.append(name[len(prefix):] if name.startswith(prefix) else name)
        return out

    # ── 컬럼·표본: **선언된 가상 노드를 통해서만** 보인다 ────────────────
    #
    # ⚠ 여기가 MindsDB 와 **뜻이 달라지는 자리**다. MindsDB 는 아무 표나
    #   `SHOW COLUMNS FROM ds.t` 로 들여다볼 수 있었다. 이 엔진에는 그 문장이
    #   없다 — 실측(2026-10-27):
    #       KEY 생략                → "expected KEY at the end of the statement"
    #       SHOW TABLES FROM ds     → 컬럼은 **개수만** 준다
    #       SHOW COLUMNS/PROPERTIES → 문법 오류
    #       AS SELECT 꼴            → 그래도 KEY 를 요구한다
    #   즉 **컬럼을 보려면 가상 노드가 필요하고, 가상 노드를 만들려면 열쇠 컬럼
    #   이름을 알아야 한다.** 임시 노드를 몰래 만들어 우회할 수 없다.
    #
    #   그래서 지어내지 않는다. 이 설계에서 **가상 노드 선언은 사람이 하는
    #   모델링**이고(어느 열쇠, 어느 속성), 선언된 뒤에는 컬럼과 표본이 전부
    #   보인다. `SHOW TABLES FROM ds` 의 세 번째 칸이 그 표에 선언된 노드
    #   이름을 주므로, 선언 여부를 사람에게 정확히 말할 수 있다.
    async def _virtual_node_of(self, database: str, table: str) -> str | None:
        ds = st.bare_name(database, "datasource name")
        qualified = st.qualified_table(database, table)
        result = await self.execute_query(f"SHOW TABLES FROM {ds}")
        if result["type"] != "table":
            raise RuntimeError("fabric table listing failed")
        cols = {name: i for i, name in enumerate(result["columns"])}
        for row in result["data"]:
            if str(row[cols.get("table", 0)]) == qualified:
                node = row[cols.get("virtual_node", 2)]
                return str(node) if node else None
        return None

    class NotDeclared(RuntimeError):
        """그 표에 가상 노드가 없다 — 사람이 선언해야 컬럼이 보인다."""

    async def _require_node(self, database: str, table: str) -> str:
        node = await self._virtual_node_of(database, table)
        if node is None:
            raise self.NotDeclared(
                f"'{st.qualified_table(database, table)}' 에는 아직 가상 노드가 없습니다. "
                "열쇠 컬럼을 정해 가상 노드를 만들면 컬럼과 표본이 보입니다."
            )
        return st.bare_name(node, "virtual node name")

    async def get_table_schema(self, database: str, table: str) -> list[dict[str, Any]]:
        """선언된 가상 노드에서 컬럼을 읽는다.

        ⚠ 타입은 **돌아온 값에서 읽은 것**이다. 선언된 타입 문자열을 주는 문장이
        없으므로, 없는 것을 지어내지 않고 **본 것만** 말한다. 값이 NULL 인 칸은
        타입을 모른다고 적는다 — `unknown` 이라고 쓰는 쪽이 틀린 타입보다 낫다.
        """
        node = await self._require_node(database, table)
        result = await self.execute_query(f"MATCH (x:{node}) RETURN x LIMIT 1")
        if result["type"] != "table" or not result["data"]:
            return []
        value = result["data"][0][0]
        properties = dict(value) if isinstance(value, Node) else {}
        return [
            {
                "name": name,
                "type": type(val).__name__ if val is not None else "unknown",
                "nullable": None,
                "key": None,
            }
            for name, val in sorted(properties.items())
        ]

    async def sample_data(self, database: str, table: str, limit: int = 10) -> dict[str, Any]:
        """선언된 가상 노드에서 표본 행을 읽는다. 경계는 파라미터로 보낸다."""
        if not 1 <= limit <= 1000:
            raise ValueError("sample limit must be between 1 and 1000")
        node = await self._require_node(database, table)
        started = time.monotonic()
        try:
            keys, records = await self._run(
                f"MATCH (x:{node}) RETURN x LIMIT $limit", {"limit": limit}
            )
        except Exception:
            logger.exception("Fabric sample failed", extra={"virtual_node": node})
            return _result("error", error="샘플 데이터 조회에 실패했습니다.")
        rows = [dict(r.get(keys[0])) if isinstance(r.get(keys[0]), Node) else {} for r in records]
        columns = sorted({k for row in rows for k in row})
        return _result(
            "table",
            columns=columns,
            data=[[row.get(c) for c in columns] for row in rows],
            execution_time=time.monotonic() - started,
        )


fabric_gateway = FabricGateway()
