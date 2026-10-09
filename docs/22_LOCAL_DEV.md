# Local development: CPU-first, Windows/macOS/Linux

## Prerequisites
- For the implemented M1 stack: Git and Docker Engine/Desktop with Compose. Python 3.13 and `uv` are needed to run tests outside containers. Node is only needed for the planned web app.
- CPU and 16GB RAM recommended for comfortable dev; core may work on less depending on running workloads; optional LLM + Kafka simultaneously may need 32GB+.
- No cloud account or model key required for core. Install dependencies from reviewed source only.

## Verified M1 commands

Create `.env` from `.env.example` and replace all five placeholders with different random local passwords of at least 16 characters. Keep `.env` out of source control. See [M1 local core](37_M1_LOCAL_CORE.md) for full setup and credential guidance.

```powershell
docker compose up --build -d --wait
docker compose exec -T api python scripts/smoke.py
docker compose down
```

The same `docker compose` commands work in a Bash shell. While the stack is running, the API readiness endpoint is `http://127.0.0.1:8000/health/ready`.

## Profiles (planned)
- `core`: api, web, postgres, worker, redis and local runner.
- `ai`: opt-in Ollama as separate/local process; graceful fallback if unavailable.
- `streaming`: Kafka/Redpanda test broker + decoder fixture + optional MQTT broker.
- `observability`: local Prometheus, Grafana and collector if resource budget permits.

Default `docker compose up` should start minimum core and avoid unnecessary heavyweight optional components. Use named volumes for DB, a clearly scoped outputs directory and explicit reset command requiring confirmation.

## Current state
M1 includes the API, worker, PostgreSQL migration, Compose stack and application tests. The PostgreSQL migration and four-row Parquet smoke run passed on 2026-10-10. See [implementation status](IMPLEMENTATION_STATUS.md) for exact results and limitations. The web app and later services remain unimplemented.

## Environment semantics (planned)
`APP_ENV=development`, `AUTH_MODE=development`, `DATABASE_URL`, `REDIS_URL`, `ENABLE_DEMO_SCENARIOS`, `LLM_PROVIDER=none`, `ENABLE_AZURE_INTEGRATION=false`, `ENABLE_LIVE_AZURE_TESTS=false`; `.env.example` has placeholders only. The demo-auth feature must be blocked in non-development environments.

## Troubleshooting checklist
Port conflicts, Docker engine, DNS, DB readiness/migrations, Redis connectivity, service health checks, worker retry loops, volume permissions, wrong API origin/CORS, Node build, Windows line endings, Ollama unavailable, streaming profile memory, Azure credential errors.

## Developer convenience
Add Makefile aliases only when commands exist, plus `scripts/dev.ps1` if practical. Pin versions/dependencies via lockfiles. On native Windows where Make isn't installed, support direct docker/python/npm commands.
