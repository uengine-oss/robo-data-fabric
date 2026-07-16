# Robo Data Fabric

Data Fabric은 데이터소스 연결의 등록·상태·수명주기와 MindsDB를 통한 실제 데이터 접근만 담당합니다.
메타데이터 추출·Neo4j Schema/Table/Column 적재·검색·보강·lineage는 이 서비스의 책임이 아니며,
Catalog가 담당합니다. 별도 웹 프론트엔드는 없고 중앙 `robo-data-frontend`가 이 API를 사용합니다.

## Runtime structure

```text
backend/app/
  main.py                         FastAPI 조립
  http/                           공개 endpoint
    datasource_endpoints.py       연결 CRUD·검사·table/schema/sample
    query_endpoints.py            MindsDB query·status
  contracts/                      Pydantic request/response 계약
  connections/                    외부 시스템 adapter
    datasource_registry.py        비밀정보 없는 Neo4j DataSource registry
    mindsdb_gateway.py             MindsDB 실제 DB 접근
    neo4j_context.py               요청별 Neo4j 연결 context
  system/settings.py              환경설정 단일 진실
backend/tests/
  unit/                            adapter 단위 계약
  contract/                        HTTP surface·보상 동작 계약
```

`DataSource` 노드는 `datasource_id`, `graph_owner='data-fabric'`, `workspace_id`를 가집니다.
대상 DB password/API key/token은 Neo4j, API 응답, 애플리케이션 로그에 저장하지 않습니다. Credential은
생성·연결검사 요청에서 MindsDB 등록으로만 전달됩니다.

## Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8404
```

환경변수는 `env.example`을 기준으로 설정합니다. 배포 manifest는 이 저장소 안에 두지 않고 workspace의
별도 배포 프로젝트에서 관리합니다.
요청별 `X-Neo4j-*` 연결 override는 기본 비활성화이며, Electron 로컬 환경에서만
`DATA_FABRIC_ALLOW_NEO4J_HEADER_OVERRIDE=true`로 명시적으로 활성화합니다.

## Public API

- `GET/POST/DELETE /api/datasources` — registry와 MindsDB 연결을 함께 관리
- `POST /api/datasources/test-connection` — 저장 없는 임시 실제 연결검사
- `GET /api/datasources/{name}/health` — MindsDB 경유 실제 DB 접근 상태
- `GET /api/datasources/{name}/tables` — 실제 테이블 목록
- `GET /api/datasources/{name}/tables/{table}/schema` — 실제 컬럼 구조
- `GET /api/datasources/{name}/tables/{table}/sample` — 제한된 실제 sample
- `POST /api/query` — MindsDB SQL 실행
- `GET /api/query/status` — MindsDB 상태

metadata extraction, materialized table, model, job, knowledge-base endpoint는 제공하지 않습니다.

## Verify

```powershell
cd backend
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
.\.venv\Scripts\python.exe -m compileall -q app tests
```

통합 완료 판정에는 실제 MindsDB·Neo4j에서 생성→table/schema/sample→삭제를 수행하고, 삭제 전후 다른
`graph_owner` 노드 수가 변하지 않는지 확인하는 E2E가 추가로 필요합니다.
