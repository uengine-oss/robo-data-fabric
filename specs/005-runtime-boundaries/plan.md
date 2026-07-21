# Implementation Plan: Runtime Boundaries

1. Record the complete folder/consumer audit.
2. Confirm no cross-domain module is stranded outside `shared` and no domain module is incorrectly inside it.
3. Run full tests, compile/import, active stale-path grep, CodeGraph, startup, and diff audit.
