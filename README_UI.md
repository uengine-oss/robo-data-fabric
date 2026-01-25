# MindsDB Data Source Manager UI

Vue 3 + FastAPI 기반의 MindsDB 데이터 소스 통합 관리 UI입니다.

## 기능

### 1. 데이터 소스 관리
- **다양한 소스 지원**: MySQL, PostgreSQL, Neo4j, MongoDB, Redis, Elasticsearch, Web Crawler, OpenAI API
- **동적 연결 폼**: 각 소스 타입에 맞는 입력 필드 자동 생성
- **테이블 탐색**: 연결된 데이터 소스의 테이블 및 스키마 확인
- **데이터 샘플링**: 실제 데이터 미리보기

### 2. SQL 쿼리 에디터
- **실시간 쿼리 실행**: MindsDB SQL API를 통한 쿼리 실행
- **결과 테이블 뷰**: 쿼리 결과를 테이블 형태로 표시
- **쿼리 히스토리**: 최근 실행한 쿼리 기록
- **Ctrl+Enter 단축키**: 빠른 쿼리 실행

### 3. Materialized Table 생성
- **CREATE TABLE AS SELECT**: 외부 소스에서 MindsDB로 데이터 복사
- **컬럼 선택**: 필요한 컬럼만 선택하여 테이블 생성
- **WHERE/LIMIT 지원**: 조건부 데이터 추출
- **SQL 미리보기**: 생성될 SQL 문 실시간 확인

### 4. MindsDB 객체 관리
- **Models**: ML 모델 목록 및 상태 확인
- **Jobs**: 스케줄된 작업 목록
- **Knowledge Bases**: 지식 베이스 목록

## 기술 스택

### Frontend
- Vue 3 (Composition API)
- TypeScript
- Tailwind CSS
- Pinia (상태 관리)
- Vue Router

### Backend
- FastAPI
- httpx (비동기 HTTP 클라이언트)
- Pydantic

## 실행 방법

### 사전 요구사항
- Python 3.9+
- Node.js 18+
- MindsDB 서버 (http://localhost:47334)

### 1. MindsDB 서버 실행
```bash
docker run -p 47334:47334 mindsdb/mindsdb
```

### 2. 백엔드 실행
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 프론트엔드 실행
```bash
cd frontend
npm install
npm run dev
```

### 4. 브라우저에서 접속
- **Frontend**: http://localhost:5173
- **Backend API Docs**: http://localhost:8000/docs
- **MindsDB**: http://localhost:47334

## API 엔드포인트

### Data Sources
- `GET /api/datasources` - 데이터 소스 목록
- `GET /api/datasources/types` - 지원하는 소스 타입
- `POST /api/datasources` - 데이터 소스 생성
- `DELETE /api/datasources/{name}` - 데이터 소스 삭제
- `GET /api/datasources/{name}/tables` - 테이블 목록
- `GET /api/datasources/{name}/tables/{table}/schema` - 테이블 스키마
- `GET /api/datasources/{name}/tables/{table}/sample` - 샘플 데이터

### Query
- `POST /api/query` - SQL 쿼리 실행
- `GET /api/query/status` - MindsDB 연결 상태
- `POST /api/query/materialized-table` - Materialized Table 생성
- `GET /api/query/models` - 모델 목록
- `GET /api/query/jobs` - 작업 목록
- `GET /api/query/knowledge-bases` - Knowledge Base 목록

## 프로젝트 구조

```
/Users/uengine/mindsdb/
├── frontend/                 # Vue 3 프론트엔드
│   ├── src/
│   │   ├── api/             # API 클라이언트
│   │   ├── components/      # UI 컴포넌트
│   │   ├── stores/          # Pinia 스토어
│   │   ├── types/           # TypeScript 타입
│   │   ├── views/           # 페이지 뷰
│   │   ├── App.vue          # 메인 앱
│   │   ├── main.ts          # 진입점
│   │   └── router.ts        # 라우터
│   └── package.json
│
├── backend/                  # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py          # FastAPI 앱
│   │   ├── routers/         # API 라우터
│   │   ├── schemas/         # Pydantic 스키마
│   │   └── services/        # MindsDB 서비스
│   └── requirements.txt
│
└── start_ui.sh              # 시작 스크립트
```

## 스크린샷

### Dashboard
- MindsDB 연결 상태 확인
- 리소스 통계 (데이터 소스, 모델, 작업, KB)

### Data Sources
- 데이터 소스 카드 선택 UI
- 동적 연결 폼
- 테이블/스키마 탐색

### Query Editor
- SQL 에디터 (Ctrl+Enter 실행)
- 결과 테이블 뷰
- 쿼리 히스토리

### Materialized Tables
- 소스 선택 및 컬럼 선택
- WHERE/LIMIT 조건
- SQL 미리보기
