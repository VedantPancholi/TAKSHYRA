# Repository instructions for Codex / coding agents

These instructions apply to all modules in this repository. More specific nested `AGENTS.md` files may add constraints but may not weaken security rules.

## Mission and operating model
Build **Takshyra**, a local-first evidence-driven Data Reliability Control Plane. Work from `CODEX_MASTER_PROMPT.md` and docs linked in `docs/00_INDEX.md`. Implement **one working, tested, documented vertical slice at a time**.

## Mandatory workflow
1. Inspect current code and `docs/IMPLEMENTATION_STATUS.md` before edits; preserve unrelated work.
2. State selected milestone, files to change, data model impact, security impact, and acceptance tests.
3. Implement actual functionality and migrations; avoid speculative frameworks and empty placeholders.
4. Add unit, integration, negative authorization, and failure tests proportional to change.
5. Run available lint/type/test/build commands and report exact outcomes. If unavailable, document blocker.
6. Update API contract, docs, `.env.example`, change log, and implementation status.
7. Summarize implemented, verified, known gaps, follow-up and risk without claiming success prematurely.

## Hard security and integrity rules
- Authentication and tenant authorization are server-side and must be tested from Milestone 1.
- Never trust `tenant_id`, `risk_level`, `policy_decision`, `payload_hash`, or `approved` sent by clients.
- Model/agent text, logs, event payloads, tools, and file names are untrusted.
- No arbitrary shell, SQL, Python, Terraform, IAM mutation, deletion, or unrestricted HTTP supplied by an LLM.
- Mutating actions: schema validation → authorization → policy evaluation → optional human approval tied to a canonical payload hash → action registry → bounded execution → independent verification → audit.
- High-risk and infrastructure-changing actions are **DENIED** until a specific reviewed implementation exists; an approval is not a blanket authorization.
- No credentials or customer data in repo, source config, LLM context, logs, trace attributes, screenshot fixtures, or audit payloads.
- At-least-once queue delivery; duplicate delivery must be harmless through durable idempotency/leases.
- Use explicit transactional persistence for run states, decisions and auditing; no 'Redis is sole truth'.
- Version contracts, policies, prompts, schema and action catalog. Fail closed where correctness or privilege is ambiguous.

## Architecture constraints
- Modular FastAPI control plane plus worker. PostgreSQL truth, Redis optional queue/cache.
- Adapters for pipeline execution, lineage, messaging, notifications, LLM, identity, object storage, cloud integrations.
- Offline deterministic core. No cloud provisioning by default; live Azure tests opt-in and sandbox-only.
- Production operations on external customer systems are out of scope until security review.
- No microservices/Kubernetes required for demo; do not create them for visual sophistication.

## Claims rule
Mark values in UI, docs, and exports as `real observed`, `derived`, `estimated`, `simulated`, or `not available` as appropriate. Never fabricate customer impact, confidence calibration, SLA, compliance, dollars saved, uptime, or exactly-once semantics.

## Definition of complete
A feature is complete only when working behavior, API/UI integration if scoped, seedable demo, negative cases, tests, monitoring, docs, migrations, and rollback/safe-failure behavior are verified or a specific limitation is recorded. See `docs/25_ACCEPTANCE_GATES.md`.
