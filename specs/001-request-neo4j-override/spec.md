# Feature Specification: 요청별 Neo4j 연결 override

**Created**: 2026-07-14
**Status**: Implementing

## Problem

Data Fabric의 DataSource 등록과 메타데이터 추출은 프로세스 `.env`의 Neo4j에만 기록됐다.
Electron에서 다른 연결을 선택해도 해당 요청이 선택 DB를 사용하지 않아 UI와 저장 결과가 갈라졌다.

## Requirements

- DataSource API는 `X-Neo4j-Uri/User/Password/Database` 헤더를 요청별로 읽는다.
- URI가 없으면 기존 `.env` 연결을 사용한다.
- ContextVar로 요청을 격리해 동시 요청의 연결이 섞이지 않는다.
- Async Neo4j driver는 uri/user/password별로 캐시하고 database는 session별로 선택한다.
- service 종료 시 생성된 모든 driver를 닫는다.
- 비밀번호를 응답·로그·영속 데이터에 추가하지 않는다.

## Acceptance

1. 서로 다른 database header를 가진 두 요청은 각 DB에 DataSource를 저장한다.
2. header 없는 기존 웹 요청은 환경설정 DB에 저장한다.
3. 한 요청 종료 후 다음 요청이 이전 override를 재사용하지 않는다.
4. 동일 연결 반복 요청은 driver를 재사용한다.
