# M1 local core: implemented interface and runbook

This is a development-only, CPU local slice. It has no production identity provider, network TLS, artifact download API, UI, Azure connection, or agent. The only executable pipeline is the seeded `orders_csv_v1`, which reads the packaged synthetic CSV. Client run bodies are limited to `{}` or `{"parameters": {}}`; paths, code, SQL, tenant identifiers, and roles are rejected.

## Services and persistence

`compose.yaml` defines PostgreSQL 17, Redis 7, FastAPI and a distinct worker. PostgreSQL stores tenants, users, memberships, pipeline definitions, runs, attempts, quality results and audit events. The worker claims queued runs with a database lease, polls the DB even if the Redis wakeup is lost, and allows at most two attempts after a stale lease. A stable per-run Parquet path and checksum manifest let a restarted worker reconcile an artifact left by a crash. File publication and the DB commit are not atomic together; this is a documented M1 limitation. The container stack has **not yet been smoke-tested in the current environment**.

## Fresh checkout commands

Choose five different random, development-only passwords of at least 16 characters in `.env`: `POSTGRES_PASSWORD`, `DEMO_A_EXECUTOR_PASSWORD`, `DEMO_A_VIEWER_PASSWORD`, `DEMO_B_EXECUTOR_PASSWORD`, `DEMO_B_VIEWER_PASSWORD`. The template values are rejected by application configuration. Keep `.env` out of source control. The API is bound to `127.0.0.1:8000`; Basic credentials travel over local HTTP and must not be exposed on a network.

PowerShell:

```powershell
Copy-Item .env.example .env
# Edit .env and replace every placeholder with a different random local password.
docker compose up --build -d --wait
docker compose exec -T api python scripts/smoke.py
docker compose logs api worker
docker compose down
```

Bash:

```bash
cp .env.example .env
# Edit .env and replace every placeholder with a different random local password.
docker compose up --build -d --wait
docker compose exec -T api python scripts/smoke.py
docker compose logs api worker
docker compose down
```

The API container runs `alembic upgrade head` and an idempotent seed before it starts. To rerun the seed: `docker compose exec api python -m takshyra.seed`. `docker compose down` preserves the database and output volumes. `docker compose down -v` deletes both volumes; use only when you intend to reset the local demo.

## Verified local test commands

With uv and Python 3.13 installed, `uv sync --extra test --python 3.13`, then `uv run --locked --extra test python -m pytest -q`, `uv run --locked --extra test ruff check takshyra tests migrations`, and `uv run --locked python scripts/validate_blueprint.py`. On Windows, a workspace cache may be needed: `$env:UV_CACHE_DIR='D:\Agentic_DataOps_Project\.uv-cache'`. Application tests use a migrated temporary SQLite database and a real Parquet file. PostgreSQL-specific migration and Compose behavior remain unverified here.

## Implemented HTTP routes

All `/api/v1` routes require HTTP Basic credentials plus `X-Tenant-Slug`. Seeded usernames are `demo-a-executor`, `demo-a-viewer`, `demo-b-executor`, and `demo-b-viewer`, each with its corresponding `.env` password. The supplied tenant slug must match a persisted membership. Viewer role can read but cannot enqueue.

| Route | Behavior |
|---|---|
| `GET /health/live` | Process liveness; no credential required. |
| `GET /health/ready` | DB query plus development config validation; no credential required. |
| `GET /api/v1/me` | Username, selected tenant and server-side role. |
| `GET /api/v1/pipelines` | Up to 100 pipelines in selected tenant. |
| `POST /api/v1/pipelines/{id}/runs` | Requires executor role and `Idempotency-Key` of 8–128 characters; returns 202 with run state. Same key and payload returns same run; changed payload returns 409. |
| `GET /api/v1/runs/{id}` | Tenant-scoped execution, quality, publication, attempts and checks; cross-tenant IDs return 404. |

The error envelope for explicit HTTP errors is `{ "error": { "code": "HTTP_403", "message": "...", "correlation_id": "UUID", "details": [] } }`. FastAPI validation errors still use its default 422 shape in M1. Pagination, rate limits and request size controls beyond schema bounds are deferred and must be added before exposure beyond local development.

## Quality and failure semantics

The runner writes Parquet from a bounded CSV fixture and verifies Parquet row metadata before replacing the manifest. Rules are `row_count_min_1` and `customer_id_null_0`, version 1. A completed transform with a failed check is `SUCCEEDED` / `FAIL` / `QUARANTINED`. A missing or invalid source is `FAILED` / `UNKNOWN` / `HELD` with a safe error code. Quality results persist separately from run and attempt status. The manifest contains checksum and row count, not raw rows.

## Rollback and limitations

The initial Alembic revision has a downgrade that drops all M1 tables, so it is destructive; back up data before any downgrade. The safe operational response to a bad deployment is to stop API and worker, preserve DB and output volumes, and deploy a forward fix. There is no M1 artifact garbage collector or quota, no PostgreSQL role separation beyond the local application credential, no DB RLS, no authenticated artifact download endpoint, and no production deployment claim.
