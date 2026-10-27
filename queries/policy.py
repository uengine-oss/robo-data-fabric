"""대상 DB read-only query를 검증하고 MindsDB native query로 조립한다."""

from __future__ import annotations

import re


_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_BLOCKED_WORDS = frozenset(
    {
        "ALTER", "ANALYZE", "ATTACH", "CALL", "COMMENT", "COPY", "CREATE",
        "DELETE", "DETACH", "DO", "DROP", "EXEC", "EXECUTE", "GRANT",
        "INSERT", "INSTALL", "INTO", "LOAD", "MERGE", "PRAGMA", "REINDEX",
        "REPLACE", "RESET", "REVOKE", "SET", "TRUNCATE", "UNLOAD", "UPDATE",
        "UPSERT", "USE", "VACUUM",
    }
)


class ReadOnlyQueryError(ValueError):
    """SQL이 Data Fabric의 단일 read-only statement 계약을 위반했다."""


def validate_read_only_query(query: str) -> str:
    """문자열·주석을 제외한 SQL 구조에서 단일 SELECT/CTE만 허용한다."""
    if not isinstance(query, str):
        raise ReadOnlyQueryError("query must be a string")
    statement = query.strip()
    if not statement:
        raise ReadOnlyQueryError("query is empty")
    if "/*!" in statement:
        raise ReadOnlyQueryError("executable comments are not allowed")
    if statement.endswith(";"):
        statement = statement[:-1].rstrip()

    visible = _visible_sql(statement)
    if ";" in visible:
        raise ReadOnlyQueryError("multiple statements are not allowed")
    words = [match.group(0).upper() for match in _WORD.finditer(visible)]
    if not words or words[0] not in {"SELECT", "WITH"}:
        raise ReadOnlyQueryError("only SELECT or WITH queries are allowed")
    blocked = _BLOCKED_WORDS.intersection(words)
    if blocked:
        raise ReadOnlyQueryError(f"query contains blocked operation: {sorted(blocked)[0]}")
    return statement


def _visible_sql(sql: str) -> str:
    """리터럴·인용 식별자·주석을 공백으로 마스킹하고 구조 오류를 거부한다."""
    chars = list(sql)
    visible = list(sql)
    index = 0
    parenthesis_depth = 0

    def mask(start: int, end: int) -> None:
        visible[start:end] = " " * (end - start)

    while index < len(chars):
        current = chars[index]
        following = chars[index + 1] if index + 1 < len(chars) else ""

        if current in {"'", '"', "`", "["}:
            closing = "]" if current == "[" else current
            start = index
            index += 1
            while index < len(chars):
                if chars[index] == "\\" and current in {"'", '"', "`"}:
                    index += 2
                    continue
                if chars[index] == closing:
                    if index + 1 < len(chars) and chars[index + 1] == closing and current != "[":
                        index += 2
                        continue
                    index += 1
                    mask(start, index)
                    break
                index += 1
            else:
                raise ReadOnlyQueryError("unterminated quoted value")
            continue

        if current == "$":
            tag_match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[index:])
            if tag_match:
                delimiter = tag_match.group(0)
                start = index
                end = sql.find(delimiter, index + len(delimiter))
                if end < 0:
                    raise ReadOnlyQueryError("unterminated dollar-quoted value")
                index = end + len(delimiter)
                mask(start, index)
                continue

        if current == "-" and following == "-":
            start = index
            newline = sql.find("\n", index + 2)
            index = len(chars) if newline < 0 else newline
            mask(start, index)
            continue
        if current == "#":
            start = index
            newline = sql.find("\n", index + 1)
            index = len(chars) if newline < 0 else newline
            mask(start, index)
            continue
        if current == "/" and following == "*":
            start = index
            end = sql.find("*/", index + 2)
            if end < 0:
                raise ReadOnlyQueryError("unterminated block comment")
            index = end + 2
            mask(start, index)
            continue

        if current == "(":
            parenthesis_depth += 1
        elif current == ")":
            parenthesis_depth -= 1
            if parenthesis_depth < 0:
                raise ReadOnlyQueryError("unbalanced parentheses")
        index += 1

    if parenthesis_depth:
        raise ReadOnlyQueryError("unbalanced parentheses")
    return "".join(visible)


# ── 사이퍼 읽기 전용 검사 ────────────────────────────────────────────────
#
# ⚠ **이것은 두 번째 자물쇠다.** 첫 자물쇠는 엔진이다 — 가상 노드는 읽기 전용이고
#    (타입 거부 + 외부 테이블 트리거), 임의 SQL 은 Bolt 로 들어오지도 못한다.
#    2026-10-27 에 여섯 방향으로 재서 전부 거절되는 것을 봤다. 그래도 여기서 한 번
#    더 막는 이유는, **거절이 어디서 났는지 사람에게 말해 줄 수 있는 자리**가
#    여기이기 때문이다. 엔진의 거절은 영어 한 줄로 온다.
_CYPHER_WRITE = frozenset(
    {
        "create", "merge", "delete", "detach", "set", "remove", "drop",
        "materialize", "foreach", "load", "call", "grant", "revoke",
    }
)


def validate_read_only_cypher(query: str) -> str:
    """읽기만 하는 사이퍼면 그대로 돌려주고, 아니면 거절한다."""
    text = (query or "").strip()
    if not text:
        raise ReadOnlyQueryError("질의가 비어 있습니다")
    if ";" in text.rstrip(";"):
        raise ReadOnlyQueryError("한 번에 한 문장만 보낼 수 있습니다")
    words = {w.lower() for w in _WORD.findall(_visible_sql(text))}
    hit = sorted(words & _CYPHER_WRITE)
    if hit:
        raise ReadOnlyQueryError(
            f"읽기 전용입니다 — '{hit[0].upper()}' 는 쓸 수 없습니다. "
            "원천 시스템에서 바꾸십시오"
        )
    return text
