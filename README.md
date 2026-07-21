# Robo Data Fabric

Data Fabric은 데이터소스 연결의 등록·상태·수명주기와 MindsDB를 통한 실제 데이터 접근만 담당합니다.
메타데이터 추출·Neo4j Schema/Table/Column 적재·검색·보강·lineage는 이 서비스의 책임이 아니며,
Catalog가 담당합니다. 별도 웹 프론트엔드는 없고 중앙 `robo-data-frontend`가 이 API를 사용합니다.

## Runtime structure

```text

  main.py                         FastAPI 조립
  api/                            공개 HTTP 경계
    datasources.py                연결 CRUD·검사
    tables.py                     table/schema/sample
    query.py                      read-only query·MindsDB status
    graph_connection.py           요청별 Neo4j override
  contracts/                      Pydantic datasource/query 계약
  credentials/                    credential·network 입력 경계
  registry/                       Neo4j DataSource registry
  mindsdb/                        MindsDB admin/table/transport와 quoting
  queries/                        SQL 정책·조립·실행 경계
  shared/                         공통 인프라
    config/settings.py            환경설정 단일 진실
tests/
  unit/                            adapter 단위 계약
  contract/                        HTTP surface·보상 동작 계약
```

`DataSource` 노드는 `datasource_id`, `graph_owner='data-fabric'`, `workspace_id`를 가집니다.
대상 DB password/API key/token은 Neo4j, API 응답, 애플리케이션 로그에 저장하지 않습니다. Credential은
생성·연결검사 요청에서 MindsDB 등록으로만 전달됩니다.

## Run

```powershell
cd D:\work\robo\project\robo-data-fabric
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8404
```

환경변수는 `env.example`을 기준으로 설정합니다. 배포 manifest는 이 저장소 안에 두지 않고 workspace의
별도 배포 프로젝트에서 관리합니다.
요청별 `X-Neo4j-*` 연결 override는 기본 비활성화이며, Electron 로컬 환경에서만
`DATA_FABRIC_ALLOW_NEO4J_HEADER_OVERRIDE=true`로 명시적으로 활성화합니다.

## Public API

- `GET/POST /api/datasources` — datasource 목록 조회와 registry/MindsDB 연결 생성
- `GET/DELETE /api/datasources/{name}` — 단일 datasource 조회와 소유권 범위 삭제
- `POST /api/datasources/test-connection` — 저장 없는 임시 실제 연결검사
- `POST /api/datasources/{name}/test` — 등록된 datasource 실제 연결검사
- `GET /api/datasources/{name}/health` — MindsDB 경유 실제 DB 접근 상태
- `GET /api/datasources/{name}/tables` — 실제 테이블 목록
- `GET /api/datasources/{name}/tables/{table}/schema` — 실제 컬럼 구조
- `GET /api/datasources/{name}/tables/{table}/sample` — 제한된 실제 sample
- `POST /api/query` — `{datasource, query, max_rows}` 대상 DB read-only SELECT/CTE 실행.
  Data Fabric이 MindsDB wrapper와 최종 행 제한을 조립하며 mutation·다중 statement를 거부합니다.
- `GET /api/query/status` — MindsDB 상태

metadata extraction, materialized table, model, job, knowledge-base endpoint는 제공하지 않습니다.
query HTTP timeout은 `DATA_FABRIC_QUERY_TIMEOUT_SECONDS`로 설정하며 기본 30초, 허용 범위는
0.1~300초입니다. HTTP timeout은 대기 상한이며 이미 시작된 대상 DB 작업의 취소를 보장하지 않습니다.
SQL scanner는 방어 계층이지 DB 권한을 대신하지 않으므로 운영 datasource 계정에도 read-only·최소 권한을
부여해야 합니다.

## Verify

```powershell
cd D:\work\robo\project\robo-data-fabric
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
.\.venv\Scripts\python.exe -m compileall -q main.py api contracts credentials registry mindsdb queries shared tests
```

통합 완료 판정에는 실제 MindsDB·Neo4j에서 생성→table/schema/sample→삭제를 수행하고, 삭제 전후 다른
`graph_owner` 노드 수가 변하지 않는지 확인하는 E2E가 추가로 필요합니다.
