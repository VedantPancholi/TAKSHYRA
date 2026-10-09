# M2 local incidents and fault lab

M2 extends the M1 local stack with deterministic demo faults, bounded retries, and tenant-scoped incidents. It remains development-only. Use the [M1 setup](37_M1_LOCAL_CORE.md) to create `.env` and start Compose.

## Run the fault lab

```powershell
docker compose up --build -d --wait
docker compose exec -T api alembic current
docker compose exec -T api python scripts/smoke.py
docker compose exec -T api python scripts/smoke_m2.py
```

The API and worker share PostgreSQL run, attempt, incident, timeline and audit records. The API stays bound to `127.0.0.1:8000`. The second smoke script uses the seeded demo executor and checks all four M2 cases through the API.

## Deterministic cases

| Code | Request or effect | Verified result |
|---|---|---|
| F02 | `{"demo_fault":"F02"}` when enqueuing | Simulated 503 on attempts 1 and 2; a third attempt succeeds. No incident is opened. |
| F03 | `{"demo_fault":"F03"}` when enqueuing | Simulated persistent 503; three attempts total, then execution `FAILED`, quality `UNKNOWN`, and an `OPEN` incident. |
| F04 | `{"demo_fault":"F04"}` when enqueuing | Drops one of four packaged rows after source read. Execution `SUCCEEDED`, source row count check `FAIL`, output `QUARANTINED`, and an incident links to the failed check. |
| F07 | `POST /api/v1/demo/pipelines/{id}/freshness-miss` with `{}` | Manually records a simulated missed freshness event and an incident with a pipeline reference and no run. |

F02 and F03 are fixed simulations; no HTTP source is contacted. F07 is manually injected; no freshness scheduler exists yet. All four cases require development authentication and an executor role. Clients cannot provide a file path, arbitrary error, tenant, code or SQL. Every M2 fault is labeled `simulated`; ordinary observed failures are labeled `real observed`.

## Incident contract

All routes require HTTP Basic and `X-Tenant-Slug` from M1. The tenant comes from stored membership. Viewer can read incidents; executor can mark an open incident `INVESTIGATING`. The first investigator becomes its owner, and another executor cannot modify it. There is no resolution transition in M2.

| Route | Behavior |
|---|---|
| `GET /api/v1/incidents` | Latest 100 incidents for the selected tenant. |
| `GET /api/v1/incidents/{id}` | One incident and up to 100 timeline events; `timeline_truncated` reports overflow. Cross-tenant IDs return 404. |
| `PATCH /api/v1/incidents/{id}` | Body `{"status":"INVESTIGATING"}` only; change is audited and added to timeline. `RESOLVED` returns 422. |

Incidents contain category, deterministic severity, fixed error code, first/last seen time, occurrence count, owner, provenance and `diagnosis_status: UNKNOWN`. Timeline events contain typed references to run, failed quality result, pipeline or incident. They contain no raw rows, passwords, arbitrary logs or model-generated diagnosis. The fingerprint combines tenant, pipeline, category, error code, provenance and UTC date. Repeated alerts within that day increment the same incident; the next UTC day starts a new incident. Evidence references are server-created within the same tenant transaction.

## Retry, failure and rollback

Retryable demo faults use at most three attempts with durable PostgreSQL `next_attempt_at` times and 1 then 2 second delays. A stale lease is reclaimed; three exhausted leases mark the run `TIMED_OUT` and open an incident. A permanent source/schema error fails immediately. Redis remains a wakeup hint and is not durable truth. Worker writes final run state, checks, incident observations and audit in one database transaction.

M2 migrations are `0002_incidents` and `0003_incident_owner`. Do not downgrade a database with real incident history: the downgrade removes incident tables. For a bad local deployment, stop API and worker, preserve volumes, and deploy a forward fix. Automated freshness monitoring, incident resolution verification, notification delivery, rate limits, production identity and customer system integrations remain outside M2.
