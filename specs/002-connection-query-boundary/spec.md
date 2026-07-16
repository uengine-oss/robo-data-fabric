# Feature Specification: Data Fabric 연결·실데이터 접근 경계

**Created**: 2026-07-17  
**Status**: Implementing

## Problem

Data Fabric은 중앙 UI가 사용하는 데이터소스 연결 관리와 실제 DB 접근 외에도, 독립 실험용 UI,
Schema/Table/Column 메타데이터 추출·Neo4j 적재, materialized table, MindsDB model/job/knowledge-base,
튜토리얼과 주택 예제를 함께 보유한다. 메타데이터 writer는 Catalog/Analyzer 그래프와 라벨·소유권이
다르고 실제 제품 소비자가 없으며, 연결 비밀번호를 `DataSource.password`로 Neo4j에 평문 저장한다.

## Requirements

- Data Fabric의 책임은 데이터소스 등록·목록·삭제·연결검사와 MindsDB를 통한 table/schema/sample/query로 제한한다.
- query 요청은 `datasource`, 대상 DB의 read-only `query`, `max_rows`를 분리해 받는다. Data Fabric이
  MindsDB native wrapper와 최종 row limit을 조립하며, 다중 statement와 쓰기·DDL·세션 제어 SQL은
  대상 DB에 전달하기 전에 거부한다.
- scanner는 syntactic 방어 계층이며 DB 권한을 대체하지 않는다. datasource credential은 read-only
  최소 권한이어야 하고 HTTP timeout 뒤 대상 DB 작업이 계속될 수 있음을 운영 계약에 명시한다.
- `DataSource`에는 안정적인 `datasource_id`, `graph_owner='data-fabric'`, workspace 식별자를 기록하되 비밀번호·API key는 기록하거나 반환하지 않는다.
- 생성 요청의 credential은 연결검사와 MindsDB 등록에만 사용하고 로그·예외·Neo4j에 남기지 않는다.
- MindsDB 등록과 registry 저장은 부분 성공이 유령 연결을 남기지 않도록 보상 동작을 갖는다.
- 삭제 기본값은 MindsDB 연결과 registry를 함께 제거하고, 해당 DataSource가 소유한 과거 metadata subtree만 정밀 정리한다.
- metadata extract SSE/sync, supported-engine introspection, Schema/Table/Column writer와 조회 API를 제거한다.
- materialized table, model, job, knowledge-base API와 전용 schema/service를 제거한다.
- 독립 `frontend/`, `README_UI.md`, `start_ui.sh`, 튜토리얼·주택 예제·sample init 자산을 제거한다.
- HTTP endpoint, API 계약, 연결 gateway, registry, 설정의 이름만 보고 책임을 알 수 있는 구조로 이동한다.

## Acceptance

1. 생성·목록·상세 응답과 Neo4j에 credential 키가 0이고 MindsDB 연결은 정상이다.
2. DataSource 한 개만 등록한 뒤 Catalog `check-data`는 분석 데이터 없음으로 응답한다.
3. table/schema/sample/query 정상·실패·timeout 경로가 명시적으로 검증된다.
   query는 SELECT/CTE만 허용하고 mutation·다중 statement는 400, datasource/길이/row limit 경계는
   request validation 오류로 응답하며, 성공 응답은 요청한 `max_rows`를 넘지 않는다.
4. 삭제 후 MindsDB와 registry에 연결이 없고 다른 owner의 노드는 불변이다.
5. metadata/frontend/실험 API·파일의 활성 소비자와 runtime 참조가 0이다.
