import unittest

from pydantic import ValidationError

from app.main import app
from app.http.datasource_endpoints import TestConnectionRequest


def test_data_fabric_surface_only_exposes_connection_and_real_data_access() -> None:
    paths = set(app.openapi()["paths"])
    removed = {
        "/api/datasources/types",
        "/api/datasources/supported-engines", "/api/datasources/{name}/schemas",
        "/api/datasources/{name}/connection", "/api/datasources/{name}/extract-metadata",
        "/api/datasources/{name}/extract-metadata-sync", "/api/query/materialized-table",
        "/api/query/models", "/api/query/jobs", "/api/query/knowledge-bases",
    }
    required = {
        "/api/datasources", "/api/datasources/test-connection", "/api/datasources/{name}/health",
        "/api/datasources/{name}/tables", "/api/datasources/{name}/tables/{table}/schema",
        "/api/datasources/{name}/tables/{table}/sample", "/api/query", "/api/query/status",
    }
    assert not (paths & removed), f"dead Data Fabric endpoints remain: {sorted(paths & removed)}"
    assert required <= paths, f"required endpoints missing: {sorted(required - paths)}"


class HttpSurfaceTest(unittest.TestCase):
    def test_only_connection_and_real_data_access_are_public(self) -> None:
        test_data_fabric_surface_only_exposes_connection_and_real_data_access()

    def test_connection_probe_validates_connector_and_port_before_gateway(self) -> None:
        with self.assertRaises(ValidationError):
            TestConnectionRequest(engine="postgres;DROP", host="127.0.0.1")
        with self.assertRaises(ValidationError):
            TestConnectionRequest(engine="postgres", host="127.0.0.1", port=70000)


if __name__ == "__main__":
    test_data_fabric_surface_only_exposes_connection_and_real_data_access()
    print("[OK] Data Fabric HTTP responsibility boundary")
