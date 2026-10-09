# Codex M1 — fully running vertical slice

Implement ONE working slice: secure local-demo authentication and tenant membership, pipeline registry, POST run, durable queued worker, deterministic synthetic CSV/JSON→Parquet transform, persisted attempt/status/row counts and at least a null/row-count quality check, GET run result, `health/live` and `health/ready`.

**Implementation sequence:** Python backend setup; PostgreSQL/Alembic migrations; demo-safe auth; typed service/repository; Redis-backed queue and worker with idempotency, timeout and lease/restart reasoning; output manifest and bounded source paths; seed; Docker Compose; minimal HTML/API docs or UI not yet required; integration tests.

**Test matrix:** seed tenant A+B/users with roles; viewer cannot execute; tenant A cannot read B run; duplicate request returns same run or 409 if payload differs; actual staged Parquet exists with validated row count; worker failure visible; rerun after crash cannot duplicate published artifact; secrets remain unlogged; `pytest` and Compose smoke tests recorded.

**Exit gate:** fresh checkout commands documented for Windows PowerShell + bash; `docker compose up --build` actually starts core; migrate/seed; API returns a real completed run and valid artifact; negative auth and worker tests pass. Update implementation status and docs with exact commands/limitations. Never fake deployment success.
