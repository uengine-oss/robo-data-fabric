import unittest

from registry.connection import Neo4jOverride, get_override, set_override
from registry.datasources import DatasourceRegistry
from registry.driver import Neo4jConfig


class ConnectionContextTest(unittest.TestCase):
    def tearDown(self) -> None:
        set_override(None)

    def test_missing_uri_uses_environment_fallback(self) -> None:
        self.assertIsNone(Neo4jOverride.from_headers({}))

    def test_headers_are_parsed_without_cross_request_state(self) -> None:
        override = Neo4jOverride.from_headers({
            "x-neo4j-uri": "bolt://selected:7687",
            "x-neo4j-user": "neo4j",
            "x-neo4j-password": "secret",
            "x-neo4j-database": "selected",
        })
        set_override(override)
        self.assertEqual(get_override(), override)
        set_override(None)
        self.assertIsNone(get_override())

    def test_override_rejects_non_neo4j_and_embedded_credentials(self) -> None:
        for uri in ("http://127.0.0.1:7687", "bolt://user:pass@127.0.0.1:7687", "bolt:///missing"):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                Neo4jOverride.from_headers({"x-neo4j-uri": uri})
        with self.assertRaises(ValueError):
            Neo4jOverride.from_headers({
                "x-neo4j-uri": "bolt://127.0.0.1:7687",
                "x-neo4j-database": "system",
            })

    def test_service_resolves_override_then_fallback(self) -> None:
        fallback = Neo4jConfig("bolt://fallback:7687", "neo4j", "fallback", "neo4j")
        service = DatasourceRegistry(fallback)
        self.assertEqual(service._resolve_config(), fallback)

        set_override(Neo4jOverride("bolt://selected:7687", "user", "secret", "other"))
        selected = service._resolve_config()
        self.assertEqual(selected.uri, "bolt://selected:7687")
        self.assertEqual(selected.database, "other")


if __name__ == "__main__":
    unittest.main()
