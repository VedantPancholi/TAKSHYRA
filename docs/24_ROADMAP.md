# Milestone roadmap — strictly incrementally executable

Every milestone requires passing its **exit gate** before new broad functionality. Some later release capabilities may take several development cycles.

| ID | Scope | Verifiable exit gate |
|---|---|---|
| M0 | Inspect repo, tooling, design, status | honest inventory and status file; documented plan |
| M1 | Local core: DB+API+worker+one pipeline+minimum auth+quality | Compose starts, migrate/seed, run CSV→Parquet, quality persisted, unauthorized blocked, tests pass |
| M2 | Failure lab and incident handling | transient and persistent failures, incidents, dedup/timeline tested |
| M3 | Policy/approval/action/audit | approve/deny, bounded retry, no unsafe action, tamper/cross-tenant tests |
| M4 | Versioned contracts and publish gate | successful transform with bad data blocked; contract version/evidence tested |
| M5 | Assets, OpenLineage, blast radius | meaningful lineage graph and bounded tenant-safe impact path tested |
| M6 | Useful operations UI | complete incident→action journey from web with role restrictions |
| M7 | Diagnosis + optional local AI + memory | structured evidence hypotheses and deterministic no-model fallback |
| M8 | Shadow replay & independent verification | isolated replay works/partial cases truthful; verify after action |
| M9 | Local streaming + opt-in Azure adapters | deterministic streaming failures; mocked Azure tests; live only opted-in |
| M10 | Hardening + benchmarks + release | security/restore/load/test matrix; documented limitations and demo |

## Vertical slice first
M1 deliberately spans API, DB, worker, runner, seed and tests; avoid building 8 isolated CRUD services before real execution works.

## Milestone cross-cutting duties
Every release includes tenant auth, validation, logging, quality/error handling, API docs, migration tests and implementation status. UI can be minimal until M6 but API always real and testable. Docs as built, not aspirational.

## Exit gate evidence in `docs/IMPLEMENTATION_STATUS.md`
Current stage, exact commands executed, exit code, test count (only actual), API endpoints actually working, failure scenarios verified, deferred items, security review notes, affected files and changes. A README statement is not proof by itself.

## Prioritization guardrail
If a milestone is too broad, split into `M4a/M4b` and keep all prior gates. Do not merge phases to speed through at the cost of correctness. Avoid adding features just because an AI coding tool can produce a lot of files.
