# Implementation Plan: Shared Layout

## Target Tree

```text
shared/config/settings.py
queries/{builder,policy}.py
main.py                       # owns its one-use logging bootstrap
```

## Slices

1. Freeze clean baseline and CodeGraph consumers.
2. Move config and all consumers; settings tests and old import 0.
3. Inline logging bootstrap and delete the one-consumer module; startup test and old import 0.
4. Move `readonly_query` to `queries`; update API/tests/docs; policy/contract tests and old path 0.
5. Full tests, compile, structure ledger, CodeGraph sync, diff audit.
