"""Build row-bounded MindsDB native queries from validated SQL."""
from __future__ import annotations

import re

from .policy import ReadOnlyQueryError, validate_read_only_query

_DATASOURCE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,127}$")


def build_mindsdb_read_query(datasource: str, query: str, max_rows: int) -> str:
    if not _DATASOURCE.fullmatch(datasource):
        raise ReadOnlyQueryError("invalid datasource identifier")
    bounded_query = validate_read_only_query(query)
    if not 1 <= max_rows <= 1000:
        raise ReadOnlyQueryError("max_rows must be between 1 and 1000")
    return (
        f"SELECT * FROM `{datasource}` ("
        f"SELECT * FROM ({bounded_query}) AS robo_bounded_query LIMIT {max_rows}"
        ")"
    )
