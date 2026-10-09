# Codex — start here (first session)

**Historical first-session prompt:** M1 implementation has begun. Check `docs/IMPLEMENTATION_STATUS.md` and `docs/37_M1_LOCAL_CORE.md` before using the instructions below. The Docker/PostgreSQL exit gate is still open.

The original first-session guidance follows. Act as staff data-platform engineer, backend engineer, security engineer, and pragmatic product lead.

## First-session instruction to paste into Codex

> Read `AGENTS.md`, `CODEX_MASTER_PROMPT.md`, `README.md`, `docs/00_INDEX.md`, `docs/24_ROADMAP.md`, `docs/25_ACCEPTANCE_GATES.md`, `docs/17_SECURITY_AND_THREAT_MODEL.md`, and `docs/04_ARCHITECTURE.md` in full. Inspect the actual files, Git status, installed tooling, operating system, and supported runtimes. Report existing versus planned functionality truthfully. First update `docs/IMPLEMENTATION_STATUS.md` with inventory, architecture decisions, run commands and a scoped plan. Then implement **Milestone 1 only**: a runnable local vertical slice with API health/readiness, PostgreSQL migrations, demo-safe authentication, one seeded pipeline definition, a queued run executed by a worker, a deterministic CSV→Parquet transformation, persisted run/attempt status, a basic quality result, an API endpoint for inspecting the result, and tests including unauthorized access. Use Docker Compose and working commands. Keep modules small. Do not attempt the full product at once. Run all available tests and fix failures. Document exactly what works, what you could not test, and the next step. Commit only if asked.

## Before any code is written
- Check whether Docker, Python, Node, and Git exist; do not assume working `make` on native Windows. Provide documented PowerShell equivalents.
- Reconcile package versions using current official release docs when Internet is allowed; if offline, choose conservative supported versions and document the choice.
- Write 3–8 implementation tasks with files, dependencies, risk, and acceptance tests. Then execute the first milestone within repo scope.
- Avoid introducing Kafka, Ollama, Kubernetes, Azure paid resources, five services, or 30 database tables for the first slice.

## Every later session
Paste the corresponding prompt in `prompts/` along with:

> Inspect `docs/IMPLEMENTATION_STATUS.md`, Git status, current code and tests. Preserve working behavior. Implement exactly this milestone's minimal acceptance slice; run checks, add negative tests, revise docs/status, and summarize verified results. Do not jump to the next milestone before its exit gate passes.

## Things never to do
- Do not announce 'implemented' based on docs, TODO comments, generated mocks, or unexecuted test commands.
- Do not invent API keys, Azure resource IDs, deployment results, benchmark numbers, or demo screenshots.
- Do not use production credentials, production datasets, or a subscription unless expressly provided and separately reviewed.
- Do not let model output bypass deterministic allowlist, tenant authorization, policy checks, or human approval.
