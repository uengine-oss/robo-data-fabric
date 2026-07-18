# Feature Specification: Data Fabric 전 파일 연결·실데이터 경계 재감사

**Created**: 2026-07-17
**Status**: In progress

## Requirements

- 모든 tracked runtime/test 파일을 다시 감사하며 spec002 체크를 최신 완료 증거로 간주하지 않는다.
- Data Fabric은 datasource 연결 등록/조회/삭제, credential 경계, 연결검사, 실제 DB schema/table/sample/
  read-only query 접근만 소유한다.
- `Neo4jService`, `MindsDBService`, generic `Settings`, 넓은 `datasource_endpoints.py`처럼 역할이
  불명확한 파일·클래스·함수·변수를 구체적인 registry/gateway/connection/read API 이름으로 바꾼다.
- metadata extraction, 독립 frontend, routers/schemas/services 과거 구조, 예제/init 잔재의 정적·동적
  소비자 0을 확인하고 제거한다.
- credential 비영속, 보상 동작, read-only query scanner와 owner-scoped delete 계약은 보존한다.
- `project_temp`에서 실행 중인 사용자 서버·포트는 건드리지 않으며 live 검증은 별도 포트로 격리한다.

## Acceptance

전체 inventory/ledger 일치, 잔재와 old ambiguous names 0, compile/full tests, 실제 MindsDB/대상 DB,
Catalog sample contract, 중앙 UI datasource 생성·조회·삭제 Playwright가 통과한다.

## GOAL-D final-structure binding

`D:/work/robo/GOAL-D/02-최종구조.md` §3 is a required executable contract.

- Move `system/settings.py` to `settings.py` with `FabricSettings`, and add the
  single-file observability owner.
- Split HTTP into `api/{datasources,tables,query,graph_connection}.py` and
  contracts into `contracts/{datasources,query}.py`.
- Extract credential allowlisting/network rewrite, datasource registry driver/
  connection/scope, MindsDB transport/quoting/admin/tables, and read-only query
  policy/builder into the exact final owners.
- Remove old `connections/http/queries/system` runtime paths and ignored empty
  legacy/frontend roots only after consumer proof.
- Every runtime file must have a final keep/move/split/delete mapping; machine
  verification must report missing 0, forbidden 0 and unclassified 0.
