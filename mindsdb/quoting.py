"""Validated MindsDB identifiers."""
import re

_CONNECTOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,127}$")
_ENGINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def safe_connector_name(value: str) -> str:
    if not isinstance(value, str) or not _CONNECTOR.fullmatch(value):
        raise ValueError("invalid database name")
    return value


def safe_engine_name(value: str) -> str:
    if not isinstance(value, str) or not _ENGINE.fullmatch(value):
        raise ValueError("invalid engine name")
    return value


def quote_identifier(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(f"invalid {field}")
    return f"`{value.replace('`', '``')}`"
