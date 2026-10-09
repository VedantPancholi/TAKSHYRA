# Test strategy, fault lab and security regression matrix

## Layers and commands (mixed implemented and planned scope)
1. Pure domain unit: state machines, schema fingerprints, quality checks, graph traversal, parser, retry classifier, policy.
2. API integration: auth/session, migrations, CRUD, pagination, idempotency, 403/404, 422, 409, 429.
3. Worker integration: queue delivery, lease reclaim, timeout, outbox recovery or explicitly documented gap, safe artifact commit.
4. System E2E: compose stack with seeded synthetic scenarios.
5. UI: typecheck/build/component tests + E2E Playwright for important journeys.
6. Security: property-based and negative tests for tenant isolation, tampered approvals, injection, secrets, privilege checks.
7. Connector: mock contract fixtures in CI; separately opted-in sandbox-only Azure live tests.
8. Performance/reliability: test load, recovery drills and measured capacity with documented environment.

## Deterministic fault scenarios
| ID | Injected condition | Expected signals | Required result |
|---|---|---|---|
| F01 | Clean daily orders | PASS checks | SUCCEEDED + PASS + PUBLISHED |
| F02 | transient source HTTP 503 twice | transient error | bounded retry then success + audit |
| F03 | persistent source unavailable | exhausted attempts | FAILED, incident OPEN, no infinite loop |
| F04 | one of four rows dropped after source read in the M2 demo | completeness FAIL | SUCCEEDED + FAIL + QUARANTINED |
| F05 | required field missing | schema FAIL | no publish, evidence/incident |
| F06 | duplicate primary keys | duplicate check FAIL | contract behavior according severity |
| F07 | no fresh data by deadline | freshness SLO fail | incident despite no run event |
| F08 | viewer attempts run/approval | authorization deny | no mutation, audit when applicable |
| F09 | tenant A requests tenant B incident | auth deny/hidden | zero cross-tenant leakage |
| F10 | tampered/expired approval | policy guard fails | no execution |
| F11 | same queued task delivered twice | duplicate dispatch | at most one intended side effect |
| F12 | prompt injection in log | injection attempt | no unsafe tool/action, evidence remains untrusted |
| F13 | worker crash mid-write | partial output | no false published output, re-scan/reconcile |
| F14 | schema v15 hits decoder v14 | DLQ/decoder exceptions | incident plus shadow test possibility |
| F15 | source/sink row mismatch after offset commit | reconciliation gap | flags quality despite offset success |
| F16 | shadow snapshot corrupted or expired | missing evidence | PARTIAL/IMPOSSIBLE, no green claim |

## Test fixture principles
Seeded RNG; fixed time via injected clock; deterministic IDs or stable semantic lookups; keep synthetic data clearly labeled. No live vendor services or LLM required for default CI. Test clean database migration from scratch.

M1 F01 and M2 F02, F03, F04 and F07 have working local API/worker tests and Compose smoke scripts. Other scenarios remain planned. F02 and F03 use fixed simulated 503 codes, and F07 uses manual injection; they do not represent a live source or automated freshness monitor. See [M2 incidents](38_M2_INCIDENTS.md).

## Reliability drills
Kill worker during leased task; stop Redis after transaction; resume after DB restart; hit duplicate approval concurrently; simulate old event arriving after new contract version; attempt replay outside broker retention. Require fail-safe outcome and durable incident/audit evidence.

## Evidence in PR
List exact commands and exit codes, environment versions and known skipped tests. Snapshot UI is not a replacement for backend negative auth tests. Do not generate fake benchmark CSVs or test pass badges.
