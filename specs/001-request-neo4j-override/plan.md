# Implementation Plan: 요청별 Neo4j 연결 override

## Flow

`Gateway request headers → router dependency → ContextVar → Neo4jService._resolve_config → connection driver cache → selected database session`

## Design

- header parsing과 ContextVar는 `connection_context.py` 한 곳이 소유한다.
- DataSource router dependency가 매 요청의 값을 설정한다.
- Neo4jService는 호출 순간 config를 resolve해 singleton service가 요청 상태를 보관하지 않게 한다.
- header가 없는 경우의 동작은 기존 config와 완전히 동일하다.

## Verification

- Python compile/import.
- header parsing, fallback, ContextVar 격리, driver cache 단위 테스트.
- 실제 Electron DataSource 등록 E2E.
