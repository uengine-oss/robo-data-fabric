# Implementation Plan

1. tracked source, ignored legacy, public HTTP, Catalog/Workspace/UI 소비자를 동결한다.
2. 모든 파일과 symbol의 이름·책임을 감사하고 explicit target map을 확정한다.
3. connection registry, MindsDB gateway, request connection, database read/query HTTP 경계를 git mv한다.
4. credential/compensation/query-safety 계약 테스트를 같은 슬라이스로 갱신한다.
5. consumer 0인 ignored frontend/legacy package 잔재를 제거하고 실제 DB·Catalog·UI를 검증한다.
