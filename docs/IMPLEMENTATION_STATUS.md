# Implementation status — verified engineering record

**Updated:** 2026-11-15
**Stage:** M0–M8 local milestones are merged into `main` (M8 PR #10, follow-up smoke PR #11). M9 first slice is on `feat/m9-streaming-azure`; no live Azure or AWS integration is verified.

## M9 first slice (2026-11-15)

- Added a seeded synthetic telemetry pipeline, six deterministic in-memory stream scenarios, tenant-scoped observation records and incident evidence for failed checks. This is a simulator, not a Kafka/Event Hubs consumer or checkpointed stream. The web console has a small stream lab.
- Added a read-only ADF `queryPipelineRuns` observer with exact resource allowlist, bounded window/pages/results, response-field filtering and mocked tests. An optional script requires explicit live opt-in and `DefaultAzureCredential`; no live Azure call was made.
- Focused M9 tests: 9 passed. Full migrated SQLite suite: 39 passed, one upstream Starlette/AnyIO deprecation warning. Ruff passed for source, tests, migrations and scripts. The documentation validator checked 87 internal links. The web Docker production build and TypeScript check passed. `docker compose up --build -d --wait` applied migration `0010_stream_observations` and reported five healthy services. The M9 web-proxy/PostgreSQL smoke passed for a stream mismatch incident, downstream potential impact and safe duplicate delivery.
- Remaining M9 scope: broker-backed stream consumption/reconciliation and additional Azure adapters. ADF observations are not yet ingested into the incident store. See [M9 first-slice behavior](45_M9_STREAMING_AZURE.md).
- A prioritized post-M9 console redesign is proposed in [UX design](19_UX_DESIGN.md); it is a design recommendation, not an implemented interface.

## M8 shadow recovery branch (2026-11-15)

Post-merge on `main` (commit `9b180a8`): `docker compose up --build -d --wait` reported all five services healthy. The existing M6 web smoke passed, followed by a complete M8 API and web-proxy smoke: F04 row deficit, supported replay, separate approver, new worker run, four restored rows, published quality pass and resolved incident. `scripts/smoke_m8.py` now makes this check repeatable in Compose CI. The unrelated local `.gitignore` edit was preserved.

- A bounded `F04` shadow replay copies the fixed source into temporary scratch storage, evaluates the bound contract without the row drop, compares row counts and publication checks, and records `SUPPORTED`, `PARTIAL` or `IMPOSSIBLE`. Scratch files are removed after the replay. The replay is not a separate process or security sandbox.
- A new `pipeline.reprocess_demo` action requires a supported report, source and contract rechecks, and exact approval by a different role. Execution queues a new local run. Its action verification still means enqueue only.
- A distinct recovery endpoint checks the finished run, source digest, bound contract, manifest, row count, persisted quality results and publication status. Only a `VERIFIED` outcome resolves the incident. Verified prior outcomes are retrieved only for matching error codes within the same tenant and never assert a confirmed cause.
- The console provides a row deficit run button, replay result, recovery proposal and separate verification button. The API supports the same flow without manually entering a proposal ID.
- Full Python suite: 30 passed, one upstream Starlette/AnyIO deprecation warning. Focused M8 API tests: 3 passed, including approval handoff, pending state, independent verification, incident reopening, memory retrieval, missing baseline and invalid recovery manifest. Ruff passed and the documentation validator checked 82 links. The web Docker production build and TypeScript check passed. An isolated PostgreSQL 17 container migrated to `0009_shadow_recovery (head)` and was removed.
- No Azure/AWS credentials or live provider calls were used. Provider mocks and opted-in sandbox tests belong to a later integration milestone. A general new-pipeline builder is outside M8. See [M8 behavior and demo](44_M8_SHADOW_RECOVERY.md).

## Reconnaissance

- Repository began with specifications, `seed/synthetic_orders.csv`, and a documentation validator. Before M1 there was no application source, migration, Compose stack, or application test.
- The original blueprint directory had no `.git` repository. Git 2.55.0 is installed. The project was renamed to `D:\Agentic_DataOps_Project\TAKSHYRA` for initial publication.
- Windows PowerShell environment. `uv` 0.11.27; uv-managed CPython 3.13.14 was installed for this milestone because pinned psycopg binary has no CPython 3.14 wheel. The Windows `python` alias does not launch; `py`, Node, and PostgreSQL command-line tools were unavailable on PATH. Docker Desktop and Compose became available for M1 verification.
- Baseline: direct CPython invocation of `scripts/validate_blueprint.py` exited 0: 19 required files and 45 relative links checked, example JSON parsed. This is documentation validation only.
- An `uv` cache under the user profile is inaccessible in this sandbox. Use `UV_CACHE_DIR` inside the workspace for local commands. Package download may still require network approval.

## M1 implementation plan

1. Add pinned Python project dependencies, application config, and local-only credential guard. Files: `pyproject.toml`, `takshyra/config.py`, `.env.example`. Risk: demo credentials must never be valid outside development. Test: auth refusal and production guard.
2. Add PostgreSQL schema and forward Alembic migration for tenant, user, membership, pipeline definition, run, attempt, quality result, and audit event. Files: `takshyra/models.py`, `migrations/`. Risk: cross-tenant FK mistakes. Test: migration plus tenant queries.
3. Add seeded demo identities and one fixed synthetic orders pipeline per tenant, authenticated API with tenant membership and role checks, idempotent enqueue, and read endpoints. Files: `takshyra/api.py`, `takshyra/seed.py`. Risk: horizontal access and forged roles. Test: viewer deny, cross-tenant 404, key mismatch 409.
4. Add database-backed leased worker with Redis wakeup, bounded CSV→Parquet runner, deterministic row/null checks, publication manifest and failure reconciliation. Files: `takshyra/worker.py`, `takshyra/runner.py`. Risk: worker crash and duplicate delivery. Test: duplicate claim, stale lease, staged artifact and failure status.
5. Add Compose, container startup/migrate/seed procedure, tests, API/local docs, and CI. Test: pytest and Compose smoke.

## M1 design decisions

- PostgreSQL holds queued runs and leases. Redis is a best-effort wakeup channel; the worker also polls PostgreSQL so queue loss does not lose work.
- A single seeded fixed pipeline reads only the packaged synthetic fixture. Clients cannot provide file paths, code, SQL, or tenant/role fields for execution.
- Development HTTP Basic authentication uses four distinct seeded PBKDF2 password hashes. It is guarded by explicit `APP_ENV=development` and Compose loopback binding; production identity is deliberately unavailable in M1.
- Publication uses a deterministic per-run artifact path and atomic manifest replacement. Database and filesystem have no shared transaction; restart reconciliation checks the manifest before attempting work again.

## M2 implementation and verification

- Selected vertical slice: deterministic F02/F03/F04/F07 fault cases, bounded retry scheduling, incident detection/deduplication, typed evidence timeline, role-protected incident reads and investigation ownership. Files: `takshyra/{api,incidents,models,runner,worker}.py`, migrations `0002_incidents` and `0003_incident_owner`, `tests/test_foundation.py`, `scripts/smoke_m2.py`, Dockerfile, CI and docs. The data model adds demo fault and next-attempt columns to runs plus tenant-scoped incident and timeline tables; no external system schema is touched.
- Security impact: demo requests accept only fixed fault codes under development authentication; tenant membership and executor role remain server-side. Incident references are created from stored run, quality and pipeline records, with no raw rows, logs, file paths or credentials in timeline payloads. Viewers can read; only an executor can start investigation, and a different executor cannot alter an owned incident. `RESOLVED` is unavailable in M2.
- F02 simulates two transient 503 errors then succeeds on attempt three. F03 simulates a persistent 503, stops after three attempts, and opens an execution incident. F04 drops one of four synthetic rows after source read; transform succeeds, quality fails, publication is quarantined, and the incident references the failed check. F07 manually injects a simulated missed freshness event without a run. These are fixed simulations, not real HTTP or automatic freshness monitoring.
- Retry schedule is durable in PostgreSQL with 1 then 2 second delays. Three exhausted leases mark the run timed out and open an incident. Incident fingerprints include tenant, pipeline, category, error code, provenance and UTC date; repeated alerts within that day increment the count and append timeline observations. Diagnosis remains explicitly `UNKNOWN`.
- Local migrated SQLite integration suite: 10 passed, one upstream Starlette/AnyIO deprecation warning. Covers retries/deadline, cap, crash recovery, quality evidence, daily dedup observations, tenant isolation, viewer denial, owner denial, forbidden resolution and exhausted leases. PostgreSQL migration `0003_incident_owner (head)` and both M1/M2 Compose smoke scripts passed. See [M2 runbook](38_M2_INCIDENTS.md).

## M3 implementation and verification

- Selected slice: server-authoritative `ALLOW`, `DENY` and `REQUIRES_APPROVAL` policy; exact-payload approval; `incident.annotate`, `notification.emit_local`, bounded `pipeline.retry_demo`, and simulated `pipeline.pause_demo`; leased, idempotent effects and independent database verification. Files: `takshyra/{actions,actions_api,api,auth,config,models,seed}.py` as applicable, migration `0004_policy_actions`, API/Compose/CI config, tests, `scripts/smoke_m3.py`, and [M3 runbook](39_M3_POLICY_ACTIONS.md). The new tables persist proposals, timeline and effects; runs gain a unique source-retry link; incident events gain safe note detail.
- Two approver accounts are seeded with distinct local passwords. The requester cannot approve their own proposal. Policy is versioned `m3-v1`; the digest binds schema version, tenant, requester, action, target, validated parameters, policy version and expiry. Membership, digest, expiry, policy and target preconditions are checked again before applying an effect. Unknown actions, arbitrary shell/SQL/cloud work, cross-tenant targets, non-transient retries and exhausted retry budgets fail closed.
- Local API tests cover allowed/denied actions, exact approval, tampering, expiry, self-approval, revoked approver role, cross-tenant access, forbidden client approval fields, duplicate execution, one retry per exhausted run, non-transient retry denial and local notification limit. The full migrated SQLite suite passed: 13 tests, one upstream Starlette/AnyIO deprecation warning. Ruff, documentation validation and `git diff --check` passed.
- Existing PostgreSQL volume migrated to `0004_policy_actions (head)`. Compose M1, M2 and M3 smoke scripts passed. M3 smoke exercises ALLOW, DENY and REQUIRES_APPROVAL through the API, verifies effects, and sends concurrent execution requests for one annotation with only one matching incident timeline effect.

## M4 implementation and verification

- Selected slice: tenant-scoped `Dataset` and immutable API-created `ContractVersion`, run-bound contract identity, typed deterministic orders checks, explicit `PASS/PUBLISHED`, `FAIL/QUARANTINED` and `UNKNOWN/HELD` outcomes, and authenticated manifest metadata. Files: `takshyra/{contracts,contracts_api,api,models,runner,seed,worker}.py`, migration `0005_contracts`, `tests/test_contracts.py`, `scripts/smoke_m4.py`, Dockerfile, CI, contract example and docs. Dataset and contract rows are new; `runs.contract_version_id` is nullable for pre-M4 history and has a tenant-composite foreign key.
- Security impact: only tenant members can read contract versions or manifests; only approver/admin can create the next version. Server chooses tenant, version and hash. No executable contract expressions, client-controlled paths or raw artifact downloads. A run pins its version at enqueue; the worker verifies stored canonical hash. PostgreSQL run status governs publication. Manifest API compares contract hash, publication/quality status and checks to DB evidence. Crash recovery checks source rows and persisted Parquet against the bound contract before reusing a manifest.
- The synthetic v1 baseline is four rows. F04 drops one of four, producing `SUCCEEDED/FAIL/QUARANTINED`. A version without a baseline yields `SUCCEEDED/UNKNOWN/HELD` for otherwise clean data. Missing required fields fail the schema check; unexpected fields follow `allow_extra_fields`. Duplicate IDs, null rates, timestamp/decimal values and optional freshness are deterministic checks.
- Local migrated SQLite integration/unit suite and PostgreSQL Compose M1–M4 smokes pass. M4 smoke uses demo-b and checks version binding, baseline-unknown hold and F04 quarantine. See [M4 runbook](40_M4_CONTRACTS.md). PR #4 subsequently passed GitHub test, Compose smoke and documentation workflows.

## Repository documentation cleanup

- Consolidated contributor workflow and safety rules in `CONTRIBUTING.md`, removed obsolete development onboarding material from the current tree, and updated the roadmap, architecture map, documentation index and validator to keep public links accurate. No data model, API, runtime configuration or application behavior changed.
- Local validation after cleanup: `uv run --locked python scripts/validate_blueprint.py` passed (15 required files, 65 internal links and example JSON); Ruff passed; `uv run --locked --extra test python -m pytest -q --tb=short` passed (17 tests, one upstream Starlette/AnyIO deprecation warning); `git diff --check` passed.

## M5 implementation and verification

- Selected slice: tenant-scoped asset registry, directed edges with provenance and validity windows, exact OpenLineage job-facet dataset mappings, idempotent event identity, bounded potential impact traversal and incident-to-output linkage. Files: `takshyra/{models,seed,api,lineage,lineage_api}.py`, migration `0006_lineage`, `tests/test_lineage.py`, `scripts/smoke_m5.py`, Dockerfile, CI and docs. Data model adds assets, lineage events and edges and a nullable tenant-checked pipeline output asset reference. No external system or cloud resource is changed.
- Security impact: tenant comes from authenticated membership; only executor/admin can ingest; reads and edges are tenant-scoped with composite foreign keys. Event size, identities, array lengths, producer URL, traversal depth and node count are bounded. Unknown top-level fields and client tenant IDs are rejected. Producer URLs are never fetched; raw facet bodies are not stored. Missing explicit lineage mapping yields no edges. Seed graph is simulated; ingested event edges are labeled as submitted metadata rather than independently verified flow.
- SQLite integration tests cover seeded independent chains, F04 incident impact, viewer access, cross-tenant denial, cycles, stale edges, depth/node truncation, explicit two-input/two-output mapping, idempotent duplicate, conflicting duplicate, invalid mapping and producer URL, and unknown impact. Full local suite passed: 20 tests, one upstream Starlette/AnyIO deprecation warning. Ruff, documentation validation and diff checks passed.
- Existing PostgreSQL volume migrated to `0006_lineage (head)`. Compose M1–M5 smoke scripts passed in order; M5 smoke checks seeded impact, F04 incident link, exact mapping and duplicate ingestion. See [M5 runbook](41_M5_LINEAGE.md). CI is updated but its execution for this branch is not yet verified.

## M6 implementation and verification

- Selected slice: Next.js and TypeScript local operations console in `apps/web/`, with sign-in, incident queue, evidence timeline, potential downstream impact, investigation ownership, annotation proposal, simulated pause approval handoff, execution and verification display. The same-origin proxy allows only the UI's API routes and bounds JSON request size. It forwards development Basic credentials and tenant slug on each request; no persistent browser or server session is created. The API remains authoritative for role, tenant, policy and approval decisions.
- Added a fifth Compose service on loopback port 3000, Node lockfile, web typecheck/build CI job and `scripts/smoke_m6.py`. The smoke covers page delivery, proxy allowlist, anonymous denial, viewer write denial, incident read, impact, annotation execution, separate approver approval and requester execution. The Next.js 16.4.4 dependency lock was audited with zero npm vulnerabilities. See [M6 runbook](42_M6_OPERATIONS_UI.md).
- Limitations: the UI keeps Basic credentials in tab memory until account switch/reload, and the user must re-enter them for each role handoff. No production identity, durable browser session, full asset explorer, real pause effect or incident resolution exists. The console is for loopback development only.

### M6 proposal handoff follow-up (2026-11-14)

- Added `GET /api/v1/action-proposals`, returning up to 50 recent summaries for the authenticated tenant. The workbench lists these actions and prioritizes pending approvals for approvers, so an account switch or page reload no longer requires typing a proposal ID. Selecting a summary fetches the full proposal through the existing tenant-scoped detail route.
- Clarified in the console and runbook that annotation stores investigation context and `pipeline.pause_demo` records only a marker. The current fixed seeded pipeline is a control-workflow demonstration, not an implementation of real pipeline repair.
- Local checks: 21 Python tests passed with one upstream Starlette/AnyIO deprecation warning; Ruff and docs validation passed; the production web image built and typechecked. The existing interactive demo stack was kept running and was not replaced for this follow-up. The updated Compose smoke is a CI gate on the branch.

## M7 diagnosis first slice (2026-11-14)

- Added tenant-scoped persisted diagnosis records, evidence snapshot hashes, rule-based hypotheses, and `GET/POST /api/v1/incidents/{id}/diagnoses`. Repeat evaluation of the same evidence returns the same record. Executor and incident-owner checks govern creation; tenant members can read their own tenant's records.
- The rules cite stored incident, run or quality-check IDs and return `UNKNOWN` when no supported rule applies. They cannot confirm a root cause. The web workbench displays the latest diagnosis and lets an executor generate one.
- The merged `main` demo was rebuilt locally with all five Compose services healthy. `scripts/smoke_m6.py` passed, including the proposal queue, approval and verification. The M7 branch was built separately so the running demo remains on merged `main`.
- M7 branch checks: 22 Python tests passed; the additional unknown-evidence case passed in a focused rerun. Ruff, the documentation validator (76 internal links), and the web production build/typecheck passed. The existing Starlette/AnyIO deprecation warning remains.
- Optional local AI, incident memory and independently verified causes remain for later M7 work. See [M7 diagnosis](43_M7_DIAGNOSIS.md).

### M7 optional local model follow-up (2026-11-14)

- Added explicitly opted-in local Ollama diagnosis using the documented JSON-schema generate API. The default remains deterministic rules. The API sends only bounded server-owned evidence cards, validates every cited evidence ID, restricts categories and next checks, and rejects `CONFIRMED` status or action fields in model output. An eight-second local timeout, response cap, fixed local-only host allowlist and disabled redirects bound the integration.
- Invalid or unavailable model results return the rule-based diagnosis. The response exposes provider status; failed attempts are recorded as safe audit events. Valid model records are reused for unchanged evidence and model identity. The console shows provider status and makes the empty verified-memory state explicit.
- No independently verified incident recovery exists yet. `similar_cases` remains empty and `memory_status` reports `NO_VERIFIED_OUTCOMES`; provisional diagnoses and M3 action-effect checks are not used as memory. M8 must supply independent recovery evidence before retrieval is enabled.
- The host has no Ollama command or listener on port 11434, so the live model path is not verified on this machine. Tests use a controlled local transport stub and cover unavailable, invalid and valid responses.
- Local verification: 27 Python tests passed (one upstream Starlette/AnyIO deprecation warning); five focused model tests passed after the final audit/timeout edits. Ruff, documentation validation (76 internal links), API Docker build and web typecheck/production build passed. The running demo was kept on merged `main`, not this follow-up branch.

## Implemented and locally verified

- Files added: `pyproject.toml`, `uv.lock`, `takshyra/{api,auth,config,db,models,runner,seed,worker}.py`, `alembic.ini`, `migrations/`, `tests/test_foundation.py`, `Dockerfile`, `compose.yaml`, `scripts/smoke.py`, `.github/workflows/m1.yml`, and `docs/37_M1_LOCAL_CORE.md`. Updated `.env.example`, `README.md`, `Makefile`, API/local docs and changelog.
- Local migrated SQLite integration tests exercise `/health/live`, `/health/ready`, `/api/v1/me` authentication dependency, pipeline listing, run enqueue, run result, role denial, cross-tenant denial, bad credentials, key reuse/conflict, unsupported request fields, worker failure, stale lease recovery, actual Parquet row metadata, checksum manifest, and quality quarantine. Explicitly tested a demo password is absent from failure logs.
- PostgreSQL migration `0001_foundation` reached head in Compose. The API and worker processed a real seeded run, produced four Parquet rows, and passed the container smoke script. The GitHub Actions workflow is present but has not executed here.

## Exact verification results

| Command | Result |
|---|---|
| Direct CPython 3.14.6 `scripts/validate_blueprint.py` before code | Exit 0; 19 required files, 45 links, JSON parsed. |
| `uv sync --extra test --python 3.14` | Failed: `psycopg-binary==3.2.6` has no CPython 3.14 wheel. |
| `uv python install 3.13` and `uv sync --extra test --python 3.13` with workspace cache | Exit 0; CPython 3.13.14 and 32 packages installed. |
| `uv run --locked --extra test ruff check takshyra tests migrations scripts/smoke.py` | Exit 0; all checks passed. |
| `uv run --locked python scripts/validate_blueprint.py` | Exit 0; 19 required files, 50 links, JSON parsed. |
| `uv run --locked --extra test pytest -q` | Failed to spawn `pytest.exe`: local Application Control policy (OS error 4551). |
| `uv run --locked --extra test python -m pytest -q` | Exit 0; 5 tests passed, 1 upstream Starlette/AnyIO deprecation warning. |
| `docker --version`, `docker info`, `docker compose version` | Docker Engine 29.8.2, Linux Docker Desktop daemon 29.8.2, Compose v5.5.1. |
| `docker compose up --build -d --wait` | Exit 0; PostgreSQL, Redis, API and worker started; Compose reported all healthy. |
| `docker compose exec -T api alembic current` | Exit 0; `0001_foundation (head)` on PostgreSQL. |
| `docker compose exec -T api python scripts/smoke.py` | Exit 0; seeded run succeeded, quality passed, publication succeeded, and Parquet metadata showed four rows. |
| `docker compose ps` after smoke | Exit 0; all four services running; API healthy and bound to `127.0.0.1:8000`. |
| M2 `uv run --locked --extra test python -m pytest -q` with workspace cache | Exit 0; 10 passed, one upstream deprecation warning. |
| M2 `uv run --locked --extra test ruff check takshyra tests migrations scripts/smoke.py scripts/smoke_m2.py` | Exit 0; all checks passed. |
| M2 `docker compose up --build -d --wait` | Exit 0; PostgreSQL, Redis, API and worker healthy after the M2 build. |
| M2 `docker compose exec -T api alembic current` | Exit 0; `0003_incident_owner (head)` on existing PostgreSQL volume. |
| M2 `docker compose exec -T api python scripts/smoke.py` | Exit 0; M1 four-row Parquet regression smoke passed. |
| M2 `docker compose exec -T api python scripts/smoke_m2.py` | Exit 0; F02 retry, F03 execution incident, F04 quality incident and F07 freshness incident passed through Compose. |
| M3 `uv run --locked --extra test python -m pytest -q` with workspace cache | Exit 0; 13 passed, one upstream deprecation warning. |
| M3 `uv run --locked --extra test ruff check takshyra tests migrations scripts` | Exit 0; all checks passed. |
| M3 `uv run --locked python scripts/validate_blueprint.py` | Exit 0; 19 required files, 61 internal links and example JSON validated. |
| M3 `docker compose up --build -d --wait` | Exit 0; PostgreSQL, Redis, API and worker healthy. |
| M3 `docker compose exec -T api alembic current` | Exit 0; `0004_policy_actions (head)` on PostgreSQL. |
| M3 `docker compose exec -T api python scripts/smoke.py` and `scripts/smoke_m2.py` | Exit 0; M1/M2 regression smokes passed. |
| M3 `docker compose exec -T api python scripts/smoke_m3.py` | Exit 0; ALLOW, DENY, approval, execution, verification and concurrent duplicate claim passed. |
| M4 `docker compose up --build -d --wait` | Exit 0; PostgreSQL, Redis, API and worker healthy. |
| M4 `docker compose exec -T api alembic current` | Exit 0; `0005_contracts (head)` on PostgreSQL. |
| M4 `docker compose exec -T api python scripts/smoke.py`, `smoke_m2.py`, `smoke_m3.py`, `smoke_m4.py` | Exit 0; M1–M4 smoke cases passed in order. |
| M4 `uv run --locked --extra test python -m pytest -q --tb=short` | Exit 0; 17 passed, one upstream Starlette/AnyIO deprecation warning. |
| M4 `uv run --locked --extra test ruff check takshyra tests migrations scripts` | Exit 0; all checks passed. |
| M4 `uv run --locked python scripts/validate_blueprint.py` | Exit 0; 19 required files, 66 internal links and example JSON validated. |
| M5 `uv run --locked --extra test python -m pytest -q --tb=short` | Exit 0; 20 passed, one upstream Starlette/AnyIO deprecation warning. |
| M5 `uv run --locked --extra test ruff check takshyra tests migrations scripts` | Exit 0; all checks passed. |
| M5 `uv run --locked python scripts/validate_blueprint.py` | Exit 0; 15 required files, 71 internal links and example JSON validated. |
| M5 `docker compose up --build -d --wait` and `alembic current` | Exit 0; four services healthy, PostgreSQL at `0006_lineage (head)`. |
| M5 `docker compose exec -T api python scripts/smoke.py` through `scripts/smoke_m5.py` | Exit 0; M1–M5 smokes passed in order. |
| M6 `docker compose up --build -d --wait` | Exit 0; PostgreSQL, Redis, API, worker and web healthy; web typecheck and production build passed. |
| M6 `docker compose exec -T api python scripts/smoke_m6.py` | Exit 0; page, proxy allowlist, viewer denial, incident, annotation, approval and verification passed. |
| M6 `npm audit` from the locked web dependency tree | Exit 0; zero vulnerabilities. |
| M6 Python Ruff and blueprint validator | Exit 0; Ruff passed; 15 required files, 74 internal Markdown links and example JSON validated. |
| M6 Python pytest suite | Exit 0; 20 passed, one upstream Starlette/AnyIO deprecation warning. |
| M6 handoff follow-up Python pytest suite | Exit 0; 21 passed, one upstream Starlette/AnyIO deprecation warning. |
| M6 handoff follow-up web Docker build | Exit 0; typecheck and Next.js production build passed without restarting the interactive demo stack. |

## Security and remaining risks

- No client-supplied execution path, role, tenant ID, code or SQL. Tenant membership and role come from persisted server records. Worker checks tenant and pipeline kind. Runs, attempts, quality and audit are durable DB records. Redis is only a wakeup hint.
- Basic credentials are suitable only for loopback development. There is no TLS, production identity, rate limit, request byte limit, DB RLS, dedicated least-privilege DB roles or independent secret scan yet. Do not expose this stack to other hosts.
- Database/filesystem publication is not atomic; deterministic manifests permit recovery of a crash after file write, but no artifact garbage collection is implemented. Output may remain on disk when a run fails after writing. Worker lease is five minutes with a maximum of two claims; a long transform may be reclaimed, and the fixed tiny fixture is the current bound.
- M1–M6 local PostgreSQL/Compose exit gates passed. M4 PR #4 also passed GitHub's application test, Compose smoke and documentation workflows. The stack remains development-only. Restore testing, metrics, production identity and operation outside loopback remain unverified or out of scope. M2 freshness injection is manual, and simulated 503 faults do not contact an HTTP source. M3 notifications are local DB records and the pause action is only simulated. `pipeline.retry_demo` verification proves durable enqueue, not downstream run success. M4 gates only Takshyra's DB visibility and manifest API; it does not atomically publish to an external consumer. M5 supports a bounded OpenLineage subset and reports potential, not confirmed, downstream impact. M8 resolves only the verified local F04 row deficit scenario. Customer-system recovery and live provider integrations are not implemented.

## Naming and repository handoff

- User-selected brand: **TAKSHYRA**; tagline **Intelligence Behind Every Decision.** Product: **Takshyra Data Reliability Platform**. Developer runtime: **Takshyra Core** (`takshyra-core` distribution, `takshyra` imports). **Takshyra AI**, **Takshyra Insight**, and **Takshyra Guardian** are planned names, not implemented AI or recovery features.
- Renamed source package, API title, Compose database/user and module commands, documentation, examples, CI paths, and local project folder.
- After rename, `uv run --locked --extra test python -m pytest -q` exited 0 (5 passed, one upstream deprecation warning); Ruff exited 0; blueprint validation exited 0 (19 required files, 50 internal links and example JSON). Docker later became available and the Compose gate passed as recorded above.
- Target repository `https://github.com/VedantPancholi/TAKSHYRA.git` returned no refs from `git ls-remote` before connection. Initial Git publication is authorized by the user's explicit request; Git commit and push outcomes must be verified separately.
- Local Git repository initialized on `main` with `origin` set to the target URL. This sandbox account differs from the directory owner, so Git commands use a repository-scoped `safe.directory` option; global Git trust settings were not changed.
