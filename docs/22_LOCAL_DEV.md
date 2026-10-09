# Local development: CPU-first, Windows/macOS/Linux

## Planned prerequisites
- Git, Docker Engine/Desktop + Compose, Python (choose supported stable 3.x and pin), Node LTS and package manager; PowerShell on Windows.
- CPU and 16GB RAM recommended for comfortable dev; core may work on less depending on running workloads; optional LLM + Kafka simultaneously may need 32GB+.
- No cloud account or model key required for core. Install dependencies from reviewed source only.

## Intended commands **after Codex implements R1**
```bash
cp .env.example .env
# edit dev-only settings; never commit .env
docker compose up --build
# document actual URLs only after verified
```
PowerShell equivalent:
```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Profiles (planned)
- `core`: api, web, postgres, worker, redis and local runner.
- `ai`: opt-in Ollama as separate/local process; graceful fallback if unavailable.
- `streaming`: Kafka/Redpanda test broker + decoder fixture + optional MQTT broker.
- `observability`: local Prometheus, Grafana and collector if resource budget permits.

Default `docker compose up` should start minimum core and avoid unnecessary heavyweight optional components. Use named volumes for DB, a clearly scoped outputs directory and explicit reset command requiring confirmation.

## Current state
M1 now includes API, worker, PostgreSQL migration, Compose configuration and an application test suite. Compose has not been run in the authoring environment because Docker is unavailable. See [M1 local core](37_M1_LOCAL_CORE.md) and [implementation status](IMPLEMENTATION_STATUS.md) for verified commands and limitations. The web app and later services remain unimplemented.

## Environment semantics (planned)
`APP_ENV=development`, `AUTH_MODE=development`, `DATABASE_URL`, `REDIS_URL`, `ENABLE_DEMO_SCENARIOS`, `LLM_PROVIDER=none`, `ENABLE_AZURE_INTEGRATION=false`, `ENABLE_LIVE_AZURE_TESTS=false`; `.env.example` has placeholders only. The demo-auth feature must be blocked in non-development environments.

## Troubleshooting checklist
Port conflicts, Docker engine, DNS, DB readiness/migrations, Redis connectivity, service health checks, worker retry loops, volume permissions, wrong API origin/CORS, Node build, Windows line endings, Ollama unavailable, streaming profile memory, Azure credential errors.

## Developer convenience
Add Makefile aliases only when commands exist, plus `scripts/dev.ps1` if practical. Pin versions/dependencies via lockfiles. On native Windows where Make isn't installed, support direct docker/python/npm commands.
