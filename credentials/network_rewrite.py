"""Request-only host rewriting for MindsDB running in a container."""
from typing import Any


def mindsdb_parameters(parameters: dict[str, Any], replacement_host: str) -> dict[str, Any]:
    result = dict(parameters)
    if result.get("host") in {"localhost", "127.0.0.1"} and replacement_host:
        result["host"] = replacement_host
    return result
