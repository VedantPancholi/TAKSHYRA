# TAKSHYRA

**Takshyra Data Reliability Platform** — an evidence-first, policy-governed Data Reliability Control Plane.

> **Tagline:** Intelligence Behind Every Decision.
> **Status:** M1 local core and M2 deterministic incident handling passed local tests and PostgreSQL/Compose smoke runs; see [implementation status](docs/IMPLEMENTATION_STATUS.md). No cloud integrations, agents, or UI are implemented.
> **Mission:** Help engineering teams determine what went wrong with data, which assets are affected, what actions are safe, and whether recovery actually restored correctness.

## The promise

Takshyra connects pipeline execution, batch/stream data quality, data contracts, lineage, evidence-driven incident investigation, safe remediation proposals, approval workflows, sandbox replay, and post-recovery verification. It observes existing orchestrators; it **does not try to replace Azure Data Factory, Fabric, Airflow, Dagster or Kafka**.

### Four questions every incident should answer
1. **What happened?** Identify technical, data quality, and freshness problems separately.
2. **What is affected?** Trace probable downstream impact through an asset graph.
3. **What can we safely do?** Produce bounded, allowlisted proposals evaluated by deterministic policy.
4. **How do we know it is fixed?** Validate invariants, lineage impact, and outcomes with durable evidence.

## Non-negotiables
- **₹0 local core**: no required subscription, cloud service, paid model, or GPU.
- **Determinism for truth**: contracts, policy, authorization, execution, and verification are not delegated to an LLM.
- **No agent directly mutates production**: proposal → policy → approval if required → registered executor → verification.
- **Evidence and explicit uncertainty**: no unsupported 'confirmed cause', fabricated benchmarks, or invented savings.
- **Security from the start**: tenant-scoped access, roles, secret redaction, least privilege, audit events.
- **Small, working increments**: vertical slices, verifiable tests, documented limitations.

## Open in this order
1. [CODEX_START_HERE.md](CODEX_START_HERE.md) — first Codex session.
2. [CODEX_MASTER_PROMPT.md](CODEX_MASTER_PROMPT.md) — complete implementation charter.
3. [AGENTS.md](AGENTS.md) — repo-wide agent instructions.
4. [docs/00_INDEX.md](docs/00_INDEX.md) — specification map.
5. [docs/24_ROADMAP.md](docs/24_ROADMAP.md) — milestone gates.

## Initial architecture
- API/control plane: **FastAPI** modular monolith, **SQLAlchemy / Alembic**, PostgreSQL.
- M1 worker: PostgreSQL-backed lease and polling with Redis wakeup; PostgreSQL is durable truth.
- Web: **Next.js + TypeScript**, with accessible operations dashboards.
- Demo processing: **DuckDB/PyArrow**, CSV/JSON/PostgreSQL → partitioned Parquet.
- Local inference: optional **Ollama**; default deterministic diagnostic engine.
- Open standards: OpenLineage-compatible events, OpenTelemetry instrumentation.
- Azure: **optional** sandbox-only adapters for ADF, Azure Monitor, Event Hubs, ADLS Gen2; Entra ID / Managed Identity / Key Vault later.

## Where the implementation will live
The M1 implementation is in `takshyra/`, `migrations/`, `tests/`, and `compose.yaml`. See [M1 local core](docs/37_M1_LOCAL_CORE.md) for commands and verified behavior.

M2 adds bounded demo faults, durable retries and tenant-scoped incidents. See [M2 incidents](docs/38_M2_INCIDENTS.md) for the supported cases, API routes and limitations.

## Demo in one sentence
Inject silent data loss into an orders pipeline or a schema break into a telemetry decoder; see an incident, evidence and impact, safe policy evaluation, optional shadow test, approval where needed, and independently verified recovery.

## Naming
The chosen platform brand is **TAKSHYRA**. The product is **Takshyra Data Reliability Platform**; **Takshyra Core** is the developer platform and the current M1 implementation. **Takshyra AI** is the planned technology umbrella, with **Takshyra Insight** for AI investigation and **Takshyra Guardian** for governed recovery. Insight and Guardian are names for future capabilities, not claims that those capabilities work today. See [docs/29_BRAND_AND_PRODUCT_STRATEGY.md](docs/29_BRAND_AND_PRODUCT_STRATEGY.md). Brand selection is not trademark clearance.

## Blueprint validation
The included `scripts/validate_blueprint.py` validates a subset of documentation references and required artifacts. It does **not** test application behavior. Application tests run with `uv run --locked --extra test python -m pytest -q`.

## Licensing
No license has been granted by this blueprint. Choose and add a license intentionally before publishing code; assess third-party dependency/model licenses separately.
