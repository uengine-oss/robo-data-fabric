"""읽기 전용 검사 — SQL 쪽(가상 노드 정의에 들어갈 것)과 사이퍼 쪽.

⚠ 2026-10-27: `build_mindsdb_read_query` 를 겨누던 시험은 걷었다. 그 함수는
   MindsDB 의 통과 질의를 감싸던 것이고, 그 통로 자체가 없어졌다(ADR-029 가 임의
   SQL 을 Bolt 로 받지 않는다). 대신 **사이퍼 읽기 전용 검사**를 겨눈다.
⚠ 이 검사는 **두 번째 자물쇠**다. 첫 자물쇠는 엔진이고(가상 노드 읽기 전용 +
   외부 테이블 트리거), 2026-10-27 에 여섯 방향으로 재서 전부 거절됨을 봤다.
"""
import unittest

from queries.policy import (
    ReadOnlyQueryError,
    validate_read_only_cypher,
    validate_read_only_query,
)


class ReadOnlySqlTest(unittest.TestCase):
    """가상 노드 정의(`AS SELECT`)에 들어갈 SQL 을 거르는 자리."""

    def test_select_passes(self):
        self.assertTrue(validate_read_only_query("SELECT 1"))

    def test_write_is_refused(self):
        for bad in ("INSERT INTO t VALUES (1)", "UPDATE t SET a = 1",
                    "DELETE FROM t", "DROP TABLE t", "TRUNCATE t"):
            with self.subTest(bad=bad), self.assertRaises(ReadOnlyQueryError):
                validate_read_only_query(bad)


class ReadOnlyCypherTest(unittest.TestCase):
    def test_match_passes(self):
        q = "MATCH (e:Emp) WHERE e.rate > 1 RETURN e.name ORDER BY e.name LIMIT 10"
        self.assertEqual(validate_read_only_cypher(q), q)

    def test_show_passes(self):
        self.assertTrue(validate_read_only_cypher("SHOW DATASOURCES"))

    def test_writes_are_refused(self):
        for bad in (
            "CREATE (:Emp {id: 1})",
            "MATCH (e:Emp) SET e.name = 'x'",
            "MATCH (e:Emp) DELETE e",
            "MATCH (e:Emp) DETACH DELETE e",
            "MERGE (e:Emp {id: 1})",
            "MATCH (e:Emp) REMOVE e.name",
            "DROP DATASOURCE loop",
            "MATERIALIZE VIRTUAL NODE Emp",
            "CALL db.index.vector.queryNodes('x', 1, [1.0])",
        ):
            with self.subTest(bad=bad), self.assertRaises(ReadOnlyQueryError):
                validate_read_only_cypher(bad)

    def test_two_statements_are_refused(self):
        with self.assertRaises(ReadOnlyQueryError):
            validate_read_only_cypher("MATCH (e:Emp) RETURN e; MATCH (d:Dept) RETURN d")

    def test_empty_is_refused(self):
        with self.assertRaises(ReadOnlyQueryError):
            validate_read_only_cypher("   ")

    def test_a_write_word_inside_a_string_does_not_trip_it(self):
        """문자열 안의 낱말로 거절하면 멀쩡한 질의가 막힌다."""
        q = "MATCH (e:Emp) WHERE e.note = 'please delete me' RETURN e.id"
        self.assertEqual(validate_read_only_cypher(q), q)


if __name__ == "__main__":
    unittest.main()
