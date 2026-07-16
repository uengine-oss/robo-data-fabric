import unittest

from app.queries.read_only_sql import (
    ReadOnlyQueryError,
    build_mindsdb_read_query,
    validate_read_only_query,
)


class ReadOnlySqlTest(unittest.TestCase):
    def test_builds_datasource_scoped_row_bounded_native_query(self) -> None:
        self.assertEqual(
            build_mindsdb_read_query("shopmall", 'SELECT * FROM "public"."orders";', 25),
            'SELECT * FROM `shopmall` (SELECT * FROM (SELECT * FROM "public"."orders") '
            'AS robo_bounded_query LIMIT 25)',
        )

    def test_allows_select_cte_and_ignores_keywords_inside_literals_or_comments(self) -> None:
        queries = (
            "SELECT 'DROP TABLE x' AS text",
            "SELECT 1 /* DELETE FROM x */",
            "WITH source AS (SELECT 1 AS id) SELECT * FROM source",
            "SELECT $$UPDATE x$$ AS text",
        )
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual(validate_read_only_query(query), query)

    def test_rejects_mutation_multi_statement_and_structural_bypass(self) -> None:
        queries = (
            "DELETE FROM orders",
            "WITH removed AS (DELETE FROM orders RETURNING *) SELECT * FROM removed",
            "SELECT * INTO backup FROM orders",
            "SELECT 1; DROP TABLE orders",
            "SELECT 1 FOR UPDATE",
            "SELECT 1 /*!; DROP TABLE orders */",
            "SELECT (1",
            "SELECT 'unterminated",
            "/* unterminated SELECT 1",
        )
        for query in queries:
            with self.subTest(query=query), self.assertRaises(ReadOnlyQueryError):
                validate_read_only_query(query)

    def test_rejects_invalid_datasource_and_row_limit(self) -> None:
        with self.assertRaises(ReadOnlyQueryError):
            build_mindsdb_read_query("shopmall) DROP DATABASE x", "SELECT 1", 1)
        with self.assertRaises(ReadOnlyQueryError):
            build_mindsdb_read_query("shopmall", "SELECT 1", 1001)


if __name__ == "__main__":
    unittest.main()
