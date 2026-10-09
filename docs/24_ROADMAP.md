# Milestone roadmap — strictly incrementally executable

Every milestone requires passing its **exit gate** before new broad functionality. Some later release capabilities may take several Codex sessions.

| ID | Scope | Verifiable exit gate | Prompt |
|---|---|---|---|
| M0 | Inspect repo, tooling, design, status | honest inventory and status file; documented plan | `prompts/00_RECONNAISSANCE.md` |
| M1 | Local core: DB+API+worker+one pipeline+minimum auth+quality | Compose starts, migrate/seed, run CSV→Parquet, quality persisted, unauthorized blocked, tests pass | `prompts/01_FOUNDATION.md` |
| M2 | Failure lab and incident handling | transient and persistent failures, incidents, dedup/timeline tested | `prompts/02_INCIDENTS.md` |
| M3 | Policy/approval/action/audit | approve/deny, bounded retry, no unsafe action, tamper/cross-tenant tests | `prompts/03_POLICY_RECOVERY.md` |
| M4 | Versioned contracts and publish gate | successful transform with bad data blocked; contract version/evidence tested | `prompts/04_CONTRACTS.md` |
| M5 | Assets, OpenLineage, blast radius | meaningful lineage graph and bounded tenant-safe impact path tested | `prompts/05_LINEAGE.md` |
| M6 | Useful operations UI | complete incident→action journey from web with role restrictions | `prompts/06_UI.md` |
| M7 | Diagnosis + optional local AI + memory | structured evidence hypotheses and deterministic no-model fallback | `prompts/07_AGENTS.md` |
| M8 | Shadow replay & independent verification | isolated replay works/partial cases truthful; verify after action | `prompts/08_SHADOW_LAB.md` |
| M9 | Local streaming + opt-in Azure adapters | deterministic streaming failures; mocked Azure tests; live only opted-in | `prompts/09_STREAMING_AZURE.md` |
| M10 | Hardening + benchmarks + release | security/restore/load/test matrix; documented limitations and demo | `prompts/10_HARDEN_RELEASE.md` |

## Vertical slice first
M1 deliberately spans API, DB, worker, runner, seed and tests; avoid building 8 isolated CRUD services before real execution works.

## Milestone cross-cutting duties
Every release includes tenant auth, validation, logging, quality/error handling, API docs, migration tests and implementation status. UI can be minimal until M6 but API always real and testable. Docs as built, not aspirational.

## Exit gate evidence in `docs/IMPLEMENTATION_STATUS.md`
Current stage, exact commands executed, exit code, test count (only actual), API endpoints actually working, failure scenarios verified, deferred items, security review notes, affected files and changes. A README statement is not proof by itself.

## Prioritization guardrail
If a milestone is too broad, split into `M4a/M4b` and keep all prior gates. Do not merge phases to speed through at the cost of correctness. Avoid adding features just because an AI coding tool can produce a lot of files.
