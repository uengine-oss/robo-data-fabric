"""Allowlisted non-secret datasource registry properties."""
from typing import Any


def registry_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    allowed = {"host", "port", "database", "user", "username", "display_name"}
    return {key: value for key, value in parameters.items() if key in allowed}
