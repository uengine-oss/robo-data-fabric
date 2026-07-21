# Feature Specification: Runtime Boundaries

**Created**: 2026-07-21
**Status**: Specified

## Goal

Verify every Data Fabric runtime folder against its consumers and retain only responsibility-accurate boundaries.

## Audit Contract

- `api`: public datasource/query/table HTTP boundary.
- `contracts`: public request/response schemas.
- `credentials`: allowlisted secret-adjacent inputs and request-only network rewriting.
- `mindsdb`: MindsDB administration, quoting, tables, and transport.
- `queries`: read-only SQL policy and bounded query construction.
- `registry`: Neo4j-backed DataSource registry and its connection scope.
- `shared/config`: process configuration consumed across bootstrap, API, registry, and MindsDB.

No additional move is justified: every runtime folder is single-word and cohesive. No generic utility folder or compatibility path may be introduced.

## Acceptance

Full 31-test suite, compile/import, active stale-path grep, CodeGraph, startup, and final tree audit pass.
