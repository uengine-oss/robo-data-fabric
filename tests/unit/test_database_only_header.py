"""`X-Neo4j-Database` 만 실은 요청이 그 graph 를 보는가 (analyzer·catalog 와 같은 계약).

**화면이 보내는 헤더는 그것 하나다.** 브라우저에서 도는 화면은 연결 자격을
클라이언트로 내보내지 않는다. `from_headers` 가 URI 없으면 `None` 을 돌려주면
그 요청은 **프로세스 환경에 고정된 graph** 로 가고, 오류는 안 난다.

catalog 쪽에서 실측한 모양(2026-09-17): 3건·7건을 심은 두 graph 를 헤더로 각각
물었는데 둘 다 `nodeCount: 0` — 환경 graph 의 값이다. **403 도 안 났다.**
override 플래그 검사가 `None` 을 안 보기 때문이다.
"""
import unittest

from registry.connection import Neo4jOverride
from shared.config.settings import settings


class DatabaseOnlyHeaderTest(unittest.TestCase):
    def test_database_only_header_selects_that_graph(self):
        override = Neo4jOverride.from_headers({"x-neo4j-database": "zz_hdr_a"})
        self.assertIsNotNone(override, "database 단독 헤더가 무시된다")
        self.assertEqual("zz_hdr_a", override.database)

    def test_database_only_header_borrows_the_configured_connection(self):
        override = Neo4jOverride.from_headers({"x-neo4j-database": "zz_hdr_a"})
        self.assertEqual(settings.neo4j_uri, override.uri)
        self.assertEqual(settings.neo4j_user, override.user)
        self.assertEqual(settings.neo4j_password, override.password)

    def test_no_header_still_falls_back_to_env(self):
        self.assertIsNone(Neo4jOverride.from_headers({}))
        self.assertIsNone(Neo4jOverride.from_headers({"x-neo4j-database": ""}))

    def test_system_database_is_refused_without_uri_too(self):
        """URI 가 있을 때만 막으면 반쪽이다 — 실제로 오는 요청에는 URI 가 없다."""
        for value in ("system", "SYSTEM"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Neo4jOverride.from_headers({"x-neo4j-database": value})


if __name__ == "__main__":
    unittest.main()
