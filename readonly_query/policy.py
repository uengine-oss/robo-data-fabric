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
