"""패브릭 문장에 들어가는 이름을 검사한다.

⚠ **이 문법에는 따옴표가 없다.** `CREATE DATASOURCE loop`·`SHOW TABLES FROM loop`·
`CREATE VIRTUAL NODE Emp FROM loop.emp KEY id` 는 모두 **맨 이름**을 받는다. MindsDB
쪽에서는 백틱으로 감쌀 수 있었지만(`mindsdb/quoting.py`), 여기서는 감쌀 수단이
없다. 그래서 **문장에 박히는 모든 이름은 여기서 거절되거나 통과한다** — 이 모듈이
유일한 문이다.

⚠ 실측(2026-10-27): `ENGINE` 은 **파라미터로 못 준다** —
`CREATE DATASOURCE x WITH ENGINE = $engine` 은
`fabric statement: expected an engine name, found '$'` 로 거절된다. 그래서 엔진
이름도 문장에 박히고, 그래서 여기서 검사한다.
반대로 `PARAMETERS` 의 **값**은 파라미터로 줄 수 있다(실측) — 비밀번호가 질의문에
안 남는 이유다. 값은 절대 문장에 박지 않는다.

⚠ MindsDB 때보다 **좁다**. 옛 규칙(`mindsdb/quoting.py`)은 이름에 `-` 를 허용했는데,
맨 이름에 하이픈이 들어가면 파서가 그것을 뺄셈으로 읽을 수 있다. 추측해서 통과시키지
않고 **거절한다** — 사람에게는 "영문·숫자·밑줄만" 이라고 말할 수 있다.
"""
from __future__ import annotations

import re

# 맨 이름으로 쓸 수 있는 것만. 하이픈·점·공백은 전부 밖이다.
_BARE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

# 엔진 이름은 제품이 아는 핸들러 이름이고, 같은 규칙으로 좁힌다.
_ENGINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,31}$")

# 예약어를 이름으로 받으면 문장이 다른 뜻이 된다. 전부 막을 수는 없지만, 문장을
# 시작할 수 있는 낱말은 막는다 — 그게 뜻이 뒤집히는 자리다.
_RESERVED = frozenset(
    {
        "create", "drop", "show", "match", "merge", "delete", "set", "remove",
        "return", "with", "where", "datasource", "virtual", "node", "relationship",
        "graph", "tables", "from", "to", "key", "properties", "engine", "parameters",
        "materialize", "explain", "fabric", "as", "select", "call",
    }
)


def bare_name(value: str, field: str) -> str:
    """문장에 박을 수 있는 이름. 아니면 거절한다."""
    if not isinstance(value, str) or not _BARE.fullmatch(value):
        raise ValueError(
            f"invalid {field}: 영문·숫자·밑줄만 쓸 수 있고 영문이나 밑줄로 시작해야 합니다"
        )
    if value.lower() in _RESERVED:
        raise ValueError(f"invalid {field}: '{value}' 는 문장에서 쓰는 낱말입니다")
    return value


def engine_name(value: str) -> str:
    """엔진 이름. `ENGINE = '<여기>'` 에 박힌다."""
    if not isinstance(value, str) or not _ENGINE.fullmatch(value):
        raise ValueError("invalid engine name")
    return value


def qualified_table(datasource: str, table: str) -> str:
    """`<ds>.<table>` — 데이터소스가 들여온 표를 가리키는 꼴.

    ⚠ 화면이 `SHOW TABLES FROM ds` 의 결과를 그대로 돌려주면 이미 `ds.` 가 붙어
    있다. 두 번 붙이지 않는다.
    """
    ds = bare_name(datasource, "datasource name")
    plain = table[len(ds) + 1:] if table.startswith(f"{ds}.") else table
    return f"{ds}.{bare_name(plain, 'table name')}"
