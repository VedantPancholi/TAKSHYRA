# Takshyra — Codex master build charter

**Read this file end to end before architecture changes. It is an implementation charter, not a request to build every module immediately.**

## 0 — Who you are
You are acting as a staff software engineer, data-platform architect, cloud integration engineer, security engineer, SRE and technical product owner. Produce a coherent engineered product, not a collection of demo screens. Optimize for correctness, explainability, maintainability and testability over tool count.

## 1 — The product we are building
**Name:** TAKSHYRA. **Product:** Takshyra Data Reliability Platform. **Category:** evidence-first, business-aware, policy-governed Data Reliability Control Plane. **Tagline:** Intelligence Behind Every Decision. Takshyra Core is the developer platform; Takshyra AI, Takshyra Insight and Takshyra Guardian are planned capability names and do not imply implementation.

The system does not replace ETL engines. It observes and manages reliability for data pipelines and data products, including local batch tasks and, later, streaming connectors (Kafka/Redpanda, Event Hubs) and Azure data systems (ADF, ADLS, Monitor, Functions, Fabric where supported).

At any point an engineer should understand:
1. Did the run execute correctly? (`execution_status`)
2. Is the output trustworthy? (`quality_status`)
3. May this output be consumed? (`publication_status`)
4. Who and what downstream may be affected? (`lineage`, impact confidence)
5. What does the evidence say about root cause? (structured hypotheses)
6. Which remediations are allowed? (policy, scope, risk, approval)
7. Did recovery actually restore the required invariants? (post-action verification)

## 2 — Primary users and jobs to be done
- **Data Engineer:** inspect failed runs, data contracts, rejected rows, safe backfills and incident timelines.
- **Platform/SRE:** see lag, DLQ growth, SLO burn, worker health and operating cost.
- **Data Product Owner:** understand freshness and impacted business assets in plain language.
- **Approver:** compare exact action, evidence, affected window, rollback option and risk before approving.
- **Auditor:** inspect who proposed, evaluated, approved, executed and verified actions without editing records.
- **Tenant Administrator:** manage membership and connector metadata only for authorized tenant.

## 3 — Non-negotiable product constraints
- Free local demo on CPU without paid LLM/cloud/paid SaaS.
- Protect tenant and user boundaries from first release.
- AI for narrative, correlation and hypotheses only; not final authority for policy, security, quality or execution.
- Every mutating action through typed registry, deterministic policy, access checks, bounded retries and audit.
- No automatic production destructive changes or arbitrary shell/SQL/cloud code.
- Test realistic failures. Expose `unknown` instead of claiming evidence not available.
- Distinguish mock/real connector status everywhere. Do not mislabel synthetic cost or model explanations.

## 4 — What to build, ordered by releases
**R1: Reliable Core.** Auth, tenant scoped pipeline registry, executable CSV/JSON→Parquet pipeline, durable run attempts, deterministic quality checks, API, basic UI, tests and Docker Compose.

**R2: Incident Intelligence.** Evidence capture, incident deduplication and timeline, diagnosis with deterministic fallback, proposed action catalog, central policy, approval and validated bounded retries.

**R3: Data Trust.** Dataset/data product registry, versioned data contracts, publish/quarantine gate, lineage from OpenLineage-compatible events, blast-radius analysis, SLO evaluation, Data Trust Passport.

**R4: Recovery Intelligence.** Incident memory of *verified* resolutions, shadow replay using retained synthetic snapshots, guardrail checks, isolated before/after comparison, post-recovery verification. Distinguish a successful simulation from proven production safety.

**R5: Streaming & Azure.** Kafka/Redpanda local fixture and failure tests; bounded Event Hubs/ADF/Azure Monitor/ADLS adapters with mocked tests and separate opt-in Azure sandbox tests; Managed Identity / Entra / Key Vault integration only where credentials/sandbox exist. Not all integrations must be live in one release.

**R6: Product hardening.** Full UI, restore drills, load tests, OpenTelemetry/metrics, security and dependency checks, measurable incident evaluation, documentation and reproducible demo.

See `docs/24_ROADMAP.md` for milestone order, dependencies, exit gates and non-goals. **Start with Milestone 1 only.**

## 5 — Logical architecture
- `apps/api`: versioned FastAPI routes, authentication and tenant authorization.
- `apps/web`: Next.js/TypeScript operations console.
- `services/worker`: durable background task orchestration and safe action execution.
- `packages/domain`: strongly typed domain models, policies, interfaces, states.
- `packages/pipeline_runner`: local data transforms and execution adapters.
- `packages/quality`: deterministic contracts/checks and publication decisions.
- `packages/incident`: correlation, evidence, incident lifecycle.
- `packages/lineage`: OpenLineage-compatible ingestion and impact traversal.
- `packages/agents`: diagnosis, remediation proposal, incident memory; no direct mutation.
- `packages/connectors`: local and optional Azure/streaming adapters.
- `packages/observability`: instrumentation and safe logging.
- `migrations`, `tests`, `seed`, `infra`, `scripts`, `docs`.

These are **logical destinations**, not instructions to create empty packages and stub endpoints. Use modular monolith first; separate process only for the worker.

## 6 — Durable model and invariants
Use PostgreSQL for durable state. Model Tenant, User, Membership, PipelineDefinition, PipelineRun, RunAttempt, Dataset, DatasetVersion, DataContract and ContractVersion, QualityResult, PublicationDecision, LineageEdge, DataProduct, SLO, Incident, IncidentEvent, IncidentEvidence, AgentExecution, RemediationProposal, PolicyDecision, Approval, ActionExecution, VerificationResult, AuditEvent, ReplaySession, ChangeEvent and optionally KnowledgeRecord.

Implement entities **incrementally**, not a speculative mega-schema. Every tenant record is tenant-scoped with database FK/uniqueness constraints and server-side authorization.

- Run lifecycle: `QUEUED -> RUNNING -> SUCCEEDED | FAILED | CANCELLED | TIMED_OUT` (terminal states guarded).
- Quality: `PENDING | PASS | WARN | FAIL | UNKNOWN` independently from execution.
- Publication: `HELD | PUBLISHED | QUARANTINED | REJECTED` independently from both.
- Proposal: `PROPOSED -> DENIED | APPROVAL_REQUIRED | ALLOWED -> EXECUTING -> VERIFYING -> VERIFIED | FAILED | INCONCLUSIVE` (formal transitions in docs).
- Idempotency keys unique per tenant and intent; payload mismatch on reused keys is conflict.
- Canonical action payload hash covers schema version, subject, tenant, scope and relevant parameters. Approval expires; actor cannot self-approve high-risk proposal. Reevaluate preconditions and policy at execution time.
- Retry budgets/leases/deadlines bounded. Event delivery is at-least-once, not exactly-once.
- Incident evidence artifacts have redaction, retention and provenance; event audit append-only through application interface.

## 7 — Quality, lineage and business-aware impact
- Implement row-count baseline, null-rate, duplicates, schema compatibility, freshness, threshold/range checks and optional distribution alerts; each check returns structured expected/observed/evidence/check version/severity/outcome.
- Evaluate contract before publishing output; use temporary staging path then atomically move/manifest-commit where feasible. A 'successful pipeline' can be quarantined.
- Ingest lineage with proper run/job/dataset identity and facets; avoid false Cartesian edges between every input and every output. Source-of-truth and inferred lineage must be tagged separately.
- Map datasets to dashboards, API dependencies and ML models as **declared demo metadata** first; use graph walk to compute impacted assets and mark potential vs confirmed impact.
- Data Trust Passport provides separate metric dimensions with freshness timestamps and evidence. Do not invent a magic universal score without a published formula and missing-data policy.

## 8 — Incidents, agents and causal discipline
- Determine incidents from deterministic rules, group by fingerprints and bounded alert windows.
- Provide incident timeline, linked run/check/asset, change correlation, redacted log refs, hypothesis ranking and provenance.
- Agents output strict Pydantic models, explicit evidence IDs, counter-evidence, uncertainty and next check. Hypothesis ranking is **not proof of causality**.
- Optional LLM provider (local Ollama first) is feature-flagged; fail gracefully to deterministic templates.
- Prevent prompt injection from source rows/logs/schemas and prevent arbitrary tool use; prompts versioned, token/time budgets, structured validation, secrets redacted.
- Incident memory indexes *verified* resolutions separately from provisional hypotheses, with retention and tenant filtering.

## 9 — Policy / safe recovery / shadow lab
Allowed early action types: `incident.annotate`, `notification.emit_local`, `pipeline.retry_demo` (bounded), `pipeline.pause_demo` (approval rules), `pipeline.replay_demo_window` (only after shadow-test and approval).

Never allow generic arbitrary shell, SQL, Python, Terraform, cloud ARM operation, IAM edit, network edit, secret access, or data deletion via an agent.

Recovery protocol:
`incident + evidence -> proposals -> authorize proposer -> deterministic policy -> optional scoped shadow run -> human approval bound to payload -> recheck state and policy -> leased action execution -> independent quality/reconciliation verification -> durable audit + incident update`.

Simulation may use captured *synthetic/authorized* snapshots. If input or external side effects cannot be reproduced, show `simulation_incomplete`. No unconditional claims of rollback.

## 10 — Reliability for streams
Model consumer group, partition, checkpoint, lag (messages and/or event-time), watermark, late data, dedupe key, DLQ, schema version, observed source/sink count reconciliation, and replay retention boundaries. A committed offset does **not** prove sink persistence. At-least-once semantics with idempotent writes and reconciliation.

## 11 — External integration discipline
Adapters expose capabilities/permissions and return typed statuses. Separate `mock`, `sandbox-live`, and `production-read-only` (only if reviewed) modes. Never auto-provision Azure. For initial ADF adapter, read/list run state and correlate safe Azure Monitor signals; runtime trigger is separately policy-gated and sandbox-only. For Event Hubs use bounded consumer-group, checkpoint, replay logic. Entra ID, Managed Identity and Key Vault never leak tokens to the frontend/LLM.

## 12 — API and UX
Version `/api/v1` with OpenAPI/Pydantic contracts, pagination, filtering, stable error envelope, correlation ID. Role/tenant permissions for every endpoint. UI surfaces: Overview, Pipelines/Runs, Data Assets & Lineage, Contracts & Trust, Incident Center, Investigation View, Remediation Approval, Shadow Lab, Audit/Policy History, Stream Health, Connector Settings, Demo Lab. Every action shows verified/mocked/simulated context, stale/missing data, loading/error/empty states and safe confirmations.

## 13 — Tests & acceptance gates
- Unit: state machine, quality checks, lineage traversal, policy, canonical hash, retry classifier.
- Integration: database migration, run/worker durability, incidents, API auth.
- Negative: tenant A/B cross-access, viewer mutation, expired/tampered approval, self-approval, duplicate delivery, prompt injection, secrets, replay out of retention.
- E2E: happy orders pipeline, transient failure→retry, persistent failure→incident, silent data loss→quarantine, schema drift→contract violation, unsafe action→DENY, approved demo retry→VERIFY, telemetry lag/schema replay.
- Evidence: record commands, environment, versions and results; do not claim 'passed' until run. No tests dependent on paid cloud/LLM.

## 14 — Cost & developer ergonomics
- `docker compose` CPU-friendly core profile; separate optional `ai`, `streaming`, `observability` profiles. Local stack should have documented resource estimates and Windows PowerShell commands.
- Required core must run offline after dependencies are installed, with deterministic seeded fake data.
- Secrets in local .env only; `.env.example` placeholders; no paid cloud provisioning.
- Terraform plan-only, budget/cleanup and least privilege for optional sandbox; disabled in CI.

## 15 — Definition of done
No placeholder success; feature complete means migrated schema, implemented code, integrated route/UI if scoped, tests for successful and failed paths, tenant/security checks, accessible screens if applicable, logs/traces, docs and commands verified. See `docs/25_ACCEPTANCE_GATES.md`.

## 16 — Execution protocol for this repository
1. Inspect actual repository; identify existing code versus blueprint, tool versions and OS.
2. Read docs index and selected milestone prompt.
3. Write/update `docs/IMPLEMENTATION_STATUS.md` with plan and verifiable tasks.
4. Implement the smallest runnable milestone, run checks, fix failures.
5. State changed files, exact commands and outcomes, blockers, remaining risks and next milestone. Do not skip milestones based on file existence.
6. Do not create Git commits or cloud resources without an explicit instruction.

**First task:** follow `prompts/01_FOUNDATION.md` after planning with `prompts/00_RECONNAISSANCE.md`. Produce real working code, not just a plan.
