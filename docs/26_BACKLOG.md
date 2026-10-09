# Prioritized product backlog and dependencies

Use IDs on issues/PRs; each story needs acceptance tests and explicit out-of-scope. These are plans, not completed tickets.

## P0 — reliable core
- `CORE-001` Auth, memberships, tenant-scoped repositories, cross-tenant tests.
- `CORE-002` Pipeline metadata CRUD + run trigger with idempotency.
- `CORE-003` Durable queue/worker claim, attempts, timeouts, crash recovery.
- `CORE-004` Deterministic CSV/JSON→Parquet with manifest and row counts.
- `CORE-005` Quality checks and separate run/quality/publish state.
- `CORE-006` Incident creation/dedup/timeline/evidence.
- `CORE-007` Typed policy engine, approval, bounded retry, audit.
- `CORE-008` Docker Compose, migrations, seeds, smoke tests and API docs.

## P1 — differentiation
- `TRUST-001` Versioned data contract and schema compatibility.
- `TRUST-002` Quality gate publication/quarantine and explicit exception audit.
- `IMPACT-001` Asset registry with owner/criticality.
- `IMPACT-002` OpenLineage event ingest, bounded lineage traversal and stale-edge handling.
- `INC-001` Evidence correlation and verified/provisional diagnosis.
- `REC-001` Isolated shadow replay and before/after report.
- `REC-002` Independent verification and incident memory.
- `STREAM-001` Kafka/Redpanda consumer lag, duplicate, DLQ and source/sink reconciliation.
- `UX-001` Complete dashboard incident workbench.

## P2 — validated experiments
- `AZURE-001` ADF run state read-only adapter and mocked tests.
- `AZURE-002` Azure Monitor bounded query adapter.
- `AZURE-003` Event Hubs sandbox streaming adapter and reconciliation.
- `AI-001` Ollama opt-in structured diagnosis, fallback and adversarial tests.
- `PRED-001` Baseline seasonal anomaly model after sufficient labeled history.
- `FIN-001` Annotated observed/simulated cost insights.
- `GROW-001` Interviews with Azure-centric SMEs; demonstrate one scenario and measure time-to-resolution.

## Sequencing
Never start PRED-001 or FIN-001 before detection/measurement and provenance are trustworthy. Do not start live Azure testing before local mocks, sandbox isolation and expense guardrails.
