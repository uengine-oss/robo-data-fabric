# Implementation Plan: Data Fabric 연결·실데이터 접근 경계

## Target Structure

```text
backend/app/
├── main.py
├── http/{datasource_endpoints,query_endpoints}.py
├── contracts/{datasource_api,query_api}.py
├── connections/{datasource_registry,mindsdb_gateway,neo4j_context}.py
├── queries/read_only_sql.py
└── system/settings.py
```

`schemas`, `routers`, `services`처럼 문맥 없는 이름을 유지하지 않는다. 데이터소스 endpoint는 요청 검증과
HTTP 변환만, registry는 Neo4j의 비밀 없는 연결 식별 정보만, MindsDB gateway는 등록과 실제 DB query만
소유한다. 과거 metadata subtree 정리는 DataSource에서 시작하는 제한된 migration query로만 수행한다.
`queries/read_only_sql.py`는 문자열 리터럴·인용 식별자·주석·괄호를 구분하는 결정론적 scanner로
단일 SELECT/CTE 계약을 검증하고, 차단 키워드와 row limit을 한 곳에서 적용한다. HTTP endpoint는
검증된 대상 SQL만 MindsDB gateway에 전달한다.

## Verification

- 전체 파일 inventory와 producer→API→consumer 검색.
- credential 비노출, 부분 실패 보상, owner 격리, 요청별 Neo4j override 단위·통합 테스트.
- 실제 MindsDB/PostgreSQL table/schema/sample/query E2E.
- mutation·다중 statement·주석/문자열 우회 반증과 실제 timeout 시간 상한.
- 중앙 UI 데이터소스 생성·목록·삭제 Playwright와 console/network 오류 검사.
