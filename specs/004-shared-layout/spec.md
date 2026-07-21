# Feature Specification: Shared Layout

**Created**: 2026-07-21
**Status**: Specified

## Goal

Move proven cross-domain Fabric configuration under a shared responsibility and replace the remaining multi-word runtime folder with a single-word domain name without changing external behavior.

## Requirements

- Move root `settings.py` to `shared/config/settings.py`.
- Inline the one-consumer `observability.py` bootstrap into `main.py`; it is not shared infrastructure.
- Rename `readonly_query/` to `queries/`.
- Preserve datasource registry, credential handling, MindsDB transport, read-only SQL policy, Neo4j override, and HTTP contracts.
- Add no compatibility aliases or duplicate implementations.

## Acceptance

Full Fabric tests, compileall, structure verifier, imports, and active old-path searches pass. Old `settings`, `observability`, and `readonly_query` paths are zero outside historical specs.
