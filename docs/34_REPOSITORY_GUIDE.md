# What belongs in the real project repository

## Permanent top-level files
- `README.md`: truthful overview; quickstart that was actually verified; screenshots only from working build.
- `AGENTS.md`: persistent rules that coding agents must follow.
- `CODEX_MASTER_PROMPT.md`, `CODEX_START_HERE.md`, `prompts/`: onboarding and milestone-specific instructions.
- `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `LICENSE` (after deliberate choice), `CODEOWNERS` if team grows.
- `.gitignore`, `.editorconfig`, `.env.example`: safe workflow.
- `pyproject.toml` + Python lockfile; frontend `package.json` + lockfile; `docker-compose.yml`; `Makefile`/PowerShell scripts **once they work**.

## Source folders created during implementation
- `apps/api/`: route handlers, auth, DI, config, versioned API, no heavy work in request thread.
- `apps/web/`: frontend pages, typed API client, components and accessibility.
- `packages/domain/`: entities, schemas, persistence ports and state machines.
- `packages/quality/`: declarative contract schemas, rule evaluators, publication gate.
- `packages/incidents/`, `packages/lineage/`, `packages/policies/`, `packages/agents/`, `packages/connectors/`, `packages/observability/` by milestone.
- `services/worker/`, `migrations/`, `seed/`, `tests/`, `scripts/`, `infra/docker/` and optional `infra/terraform/`.

## Testing folders by purpose
`tests/unit`, `tests/integration`, `tests/api`, `tests/security`, `tests/e2e`, `tests/faults`, `tests/connectors`, `tests/performance`; add only when needed. Fixtures have stable IDs and seeds, with no real customer data.

## Documentation in Git
Product problem, personas, domain glossary, technical ADRs, architecture, API and state specifications, threat model, validation strategy, feature roadmap, runbooks, licensing/cost assumptions, demo playbook and implementation-status evidence. Each substantial change updates its owning doc rather than appending to giant stale prompts.

## CI and release assets
Real GitHub Actions jobs for Python lint/type/test, frontend typecheck/build, migrations, docs links, secret scan, dependency audit, optional image vulnerability scan. Each job must fail when required checks don't run. Generate release tags/changelog only after verified feature milestone.

## What **not** to commit
`.env`, API keys/token dumps, real source data, log payloads containing PII, `.terraform` state, cloud plan outputs containing secrets, downloaded model weights without license review, raw traces, large Parquet output, databases, generated `node_modules`, `.venv`, build directories, synthetic benchmark claims, incomplete screenshots presented as product.

## Scope-control principle
A clean repository with 20 working files is better than 200 empty wrappers. Starting with a blueprint is intentional; app scaffolding is created only as tasks make it usable.
