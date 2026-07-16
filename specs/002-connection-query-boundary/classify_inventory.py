"""R1B Data Fabric 전 파일 감사 판정을 명시 규칙으로 기록한다."""
from __future__ import annotations

import csv
from pathlib import Path

from record_inventory import FIELDS, LEDGER, REPO


REMOVED_EXPERIMENTS = {
    "docker-compose.yml", "house_sales_forecasting.py", "house_sales_setup.sql",
    "init-scripts/01_create_sample_tables.sql", "quickstart_tutorial.py", "README_UI.md",
    "start_ui.sh", "tutorial_http.py",
}
REMOVED_OLD_PATHS = {
    "backend/app/routers/__init__.py", "backend/app/routers/datasources.py", "backend/app/routers/query.py",
    "backend/app/schemas/__init__.py", "backend/app/schemas/datasource.py", "backend/app/schemas/query.py",
    "backend/app/services/__init__.py", "backend/app/services/connection_context.py",
    "backend/app/services/mindsdb_service.py", "backend/app/services/neo4j_service.py",
    "backend/app/services/test_connection_context.py",
}


def _base(path: str) -> dict[str, str]:
    return {field: "" for field in FIELDS} | {"path": path}


def classify(path: str) -> dict[str, str]:
    row = _base(path)
    exists = (REPO / path).is_file()

    if path.startswith("frontend/"):
        return row | {
            "responsibility": "removed standalone prototype UI",
            "producer": "former Vite-only Data Fabric frontend",
            "consumer": "no production consumer; central robo-data-frontend is the supported UI",
            "maintainability_dry_naming": "duplicate UI/state/API surface removed",
            "dependencies_contracts": "no workspace import or runtime route consumed this package",
            "errors_operations": "removes a second startup/build path and stale endpoint behavior",
            "performance_security_generality": "removes unused npm supply-chain and credential form copy",
            "docs_tests": "repo-wide reference search 0; central UI contract test remains",
            "decision": "deleted", "evidence": "vertical frontend removal; tracked history recoverable by Git",
        }

    if path in REMOVED_EXPERIMENTS:
        return row | {
            "responsibility": "removed demo, sample data, or internal deployment artifact",
            "producer": "former local tutorial/sample workflow",
            "consumer": "no production runtime consumer",
            "maintainability_dry_naming": "lab-only workflow removed from service root",
            "dependencies_contracts": "not imported by backend or central UI",
            "errors_operations": "removes misleading alternate startup/deploy path",
            "performance_security_generality": "removes fixed sample credentials and dataset-specific behavior",
            "docs_tests": "static consumer search 0; README now documents supported runtime",
            "decision": "deleted", "evidence": "goal-approved experiment and internal deploy cleanup",
        }

    if path == "backend/app/services/schema_introspection.py":
        return row | {
            "responsibility": "removed LLM-free metadata extraction and Neo4j writer",
            "producer": "former extraction endpoints",
            "consumer": "former standalone/central extraction UI; both removed",
            "maintainability_dry_naming": "Catalog-overlapping responsibility removed",
            "dependencies_contracts": "Schema/Table/Column writer and SSE contracts retired end-to-end",
            "errors_operations": "removes silent partial extraction and plaintext credential update paths",
            "performance_security_generality": "removes DB-driver fanout, raw SQL construction, and credential persistence",
            "docs_tests": "HTTP removed-surface test and rg consumer-zero evidence",
            "decision": "deleted", "evidence": "metadata vertical slice removed with asyncpg/aiomysql/pymysql",
        }

    if path in {"backend/pyproject.toml", "backend/uv.lock"}:
        return row | {
            "responsibility": "removed unused dependency manifest",
            "producer": "former uv experiment",
            "consumer": "none; Docker and README use requirements.txt",
            "maintainability_dry_naming": "dependency SSOT restored",
            "dependencies_contracts": "eliminates stale extraction drivers and Python 3.13 drift",
            "errors_operations": "one install path remains",
            "performance_security_generality": "smaller dependency surface",
            "docs_tests": "requirements install path documented",
            "decision": "deleted", "evidence": "actual execution path inspection",
        }

    if path in REMOVED_OLD_PATHS:
        return row | {
            "responsibility": "superseded ambiguous technical-layer path",
            "producer": "git-moved during spec 002",
            "consumer": "all imports moved to http/contracts/connections",
            "maintainability_dry_naming": "responsibility-bearing name replaces routers/schemas/services",
            "dependencies_contracts": "public HTTP shape preserved except explicitly retired endpoints",
            "errors_operations": "move verified by imports and compile",
            "performance_security_generality": "no compatibility mirror retained",
            "docs_tests": "rg old imports 0; 16 tests pass",
            "decision": "deleted", "evidence": "git mv history maps to final responsibility package",
        }

    if path.startswith("backend/app/connections/"):
        return row | {
            "responsibility": "external connection adapter or request-scoped Neo4j context",
            "producer": "HTTP endpoints and process lifecycle",
            "consumer": "datasource/query endpoints",
            "maintainability_dry_naming": "one adapter per external boundary; explicit registry/gateway names",
            "dependencies_contracts": "Neo4j registry and MindsDB API isolated behind stable methods",
            "errors_operations": "driver close, timeouts, compensation inputs, and failure results are explicit",
            "performance_security_generality": "driver cache; identifier escaping; DataSource credentials excluded from registry",
            "docs_tests": "unit contracts plus compile and OpenAPI checks",
            "decision": "fixed", "evidence": "spec 002 connection boundary implementation",
        }

    if path.startswith("backend/app/http/"):
        return row | {
            "responsibility": "public Data Fabric HTTP boundary",
            "producer": "FastAPI request and dependency injection",
            "consumer": "central frontend, Catalog client, operators",
            "maintainability_dry_naming": "connection/query endpoint responsibilities separated",
            "dependencies_contracts": "removed metadata/ML demo endpoints; preserved CRUD/table/schema/sample/query",
            "errors_operations": "sanitized failures and create compensation; bounded sample limit",
            "performance_security_generality": "credentials only forwarded to MindsDB; no secret logging",
            "docs_tests": "OpenAPI removed/required route contract",
            "decision": "fixed", "evidence": "HTTP surface contract and 16-test suite pass",
        }

    if path.startswith("backend/app/contracts/"):
        return row | {
            "responsibility": "public request/response schema",
            "producer": "FastAPI validation",
            "consumer": "HTTP endpoints and OpenAPI clients",
            "maintainability_dry_naming": "API contracts separated from persistence models",
            "dependencies_contracts": "connector names and response secret exclusion are explicit",
            "errors_operations": "invalid names fail at request validation",
            "performance_security_generality": "generic engine string; mutable defaults avoided",
            "docs_tests": "OpenAPI and saga tests",
            "decision": "fixed", "evidence": "contract simplification and duplicate type catalog removal",
        }

    if path.startswith("backend/tests/"):
        return row | {
            "responsibility": "unit or public contract verification",
            "producer": "unittest discovery",
            "consumer": "maintainers and CI",
            "maintainability_dry_naming": "tests mirror runtime responsibility packages",
            "dependencies_contracts": "registry, gateway, context, HTTP, and saga contracts fixed",
            "errors_operations": "normal and compensation failure paths covered",
            "performance_security_generality": "credential and injection boundaries asserted without network secrets",
            "docs_tests": "16 tests discovered and passed",
            "decision": "fixed", "evidence": "python -m unittest discover -s tests -t .",
        }

    if path.startswith("specs/002-"):
        return row | {
            "responsibility": "R1B SDD and exhaustive audit evidence",
            "producer": "Goal requirements and current repository inspection",
            "consumer": "implementation, reviewer, continuation handoff",
            "maintainability_dry_naming": "target responsibility and completion gates are explicit",
            "dependencies_contracts": "producer-to-consumer and owner lifecycle recorded",
            "errors_operations": "rollback, compensation, timeout, and partial failure tasks retained",
            "performance_security_generality": "credential, identifier, and cross-owner risks included",
            "docs_tests": "pending E2E remains unchecked rather than overstated",
            "decision": "fixed", "evidence": "spec 002 SDD and baseline/current union ledger",
        }

    if path.startswith("specs/001-"):
        return row | {
            "responsibility": "historical request-scoped Neo4j override contract",
            "producer": "spec 001",
            "consumer": "neo4j_context and registry tests",
            "maintainability_dry_naming": "historical contract retained without compatibility code",
            "dependencies_contracts": "still valid; lifecycle portions superseded by spec 002",
            "errors_operations": "request isolation and fallback documented",
            "performance_security_generality": "secret nonlogging remains required",
            "docs_tests": "three context tests pass",
            "decision": "fixed" if path.endswith("spec.md") else "no-violation",
            "evidence": "spec status aligned; implementation contract remains live",
        }

    current_files = {
        ".gitignore": ("repository ignore policy", "Git", "developers and CI", "no-violation"),
        "backend/.dockerignore": ("container build exclusion policy", "Docker build", "Docker daemon", "no-violation"),
        "backend/Dockerfile": ("backend container build", "container builder", "external deploy project", "fixed"),
        "backend/app/__init__.py": ("application package marker", "Python import system", "all app modules", "no-violation"),
        "backend/app/main.py": ("FastAPI composition root", "process startup", "HTTP server", "fixed"),
        "backend/app/system/__init__.py": ("system package marker", "Python import system", "settings importers", "no-violation"),
        "backend/app/system/settings.py": ("process configuration SSOT", "environment", "main and adapters", "fixed"),
        "backend/requirements.txt": ("runtime dependency SSOT", "pip/Docker", "backend runtime", "fixed"),
        "env.example": ("non-secret environment template", "maintainer", "operators", "fixed"),
        "README.md": ("supported service contract and runbook", "maintainer", "developers/operators", "fixed"),
    }
    if path in current_files:
        responsibility, producer, consumer, decision = current_files[path]
        return row | {
            "responsibility": responsibility, "producer": producer, "consumer": consumer,
            "maintainability_dry_naming": "single current path; obsolete UI/deploy wording removed",
            "dependencies_contracts": "matches actual requirements, package structure, and API boundary",
            "errors_operations": "startup/config behavior is explicit; failures not silently ignored",
            "performance_security_generality": "no embedded application secret or sample-specific branch",
            "docs_tests": "README commands, compile, OpenAPI, and unit contracts inspected",
            "decision": decision, "evidence": "current file content inspected in R1B audit",
        }

    raise RuntimeError(f"unclassified audit path: {path}")


def main() -> None:
    with LEDGER.open(encoding="utf-8", newline="") as stream:
        paths = [row["path"] for row in csv.DictReader(stream, delimiter="\t")]
    rows = [classify(path) for path in paths]
    with LEDGER.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"classified={len(rows)} pending={sum(row['decision'] == 'pending' for row in rows)}")


if __name__ == "__main__":
    main()
