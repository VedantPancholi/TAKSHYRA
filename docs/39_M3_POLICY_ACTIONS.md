# M3 local policy, approvals and actions

M3 adds server-authoritative policy and four bounded local actions to the development stack. It does not grant arbitrary shell, SQL, Python, cloud, deletion or infrastructure execution. The API is still loopback-only with development HTTP Basic authentication.

## Setup and smoke

The current `.env.example` requires seven distinct local passwords: PostgreSQL plus executor, viewer and approver for each demo tenant. Add `DEMO_A_APPROVER_PASSWORD` and `DEMO_B_APPROVER_PASSWORD` to an existing ignored `.env` before starting Compose. The seed creates `demo-a-approver` and `demo-b-approver`; only their own tenant's proposals are visible.

```powershell
docker compose up --build -d --wait
docker compose exec -T api alembic current
docker compose exec -T api python scripts/smoke.py
docker compose exec -T api python scripts/smoke_m2.py
docker compose exec -T api python scripts/smoke_m3.py
```

The migration head is `0004_policy_actions`. Existing PostgreSQL and output volumes are preserved by `docker compose down`; do not use `down -v` unless deliberately resetting the demo.

## API flow

All routes require Basic credentials and `X-Tenant-Slug`. A proposal request has only `action_type`, `target_id` and `parameters`; it also requires an 8–128 character `Idempotency-Key` header. Client-supplied tenant, policy result, risk, hash and approval fields are rejected.

| Route | Role | Meaning |
|---|---|---|
| `POST /api/v1/action-proposals` | executor | Evaluate policy, persist the exact proposal and return `ALLOW`, `DENY` or `REQUIRES_APPROVAL`. |
| `GET /api/v1/action-proposals/{id}` | tenant member | Inspect exact payload digest, decision, state, verification and timeline. |
| `POST /api/v1/action-proposals/{id}/approve` | approver | Approve the immutable payload before its ten-minute expiry. The requester cannot approve their own proposal. |
| `POST /api/v1/action-proposals/{id}/execute` | original executor | Recheck policy, roles, tenant, approval and preconditions, claim a 30-second lease, apply one registered effect, then verify from a new database session. |

For example, annotate an incident with `{"action_type":"incident.annotate","target_id":"<incident UUID>","parameters":{"note":"Checked sample rows"}}`. The server stores an HTML-escaped note in the incident timeline. No approval is needed for that action.

## Registered actions

| Action | Policy | Bound and effect |
|---|---|---|
| `incident.annotate` | ALLOW | One short note on a tenant incident; HTML-escaped timeline text. |
| `notification.emit_local` | ALLOW | One fixed message code in a database-backed local sink; at most three sent effects per incident per UTC day under normal sequential use. No email or network delivery. |
| `pipeline.retry_demo` | REQUIRES_APPROVAL | Only a run timed out after three exhausted leases. Creates at most one new run linked to the source run. No retry of non-transient or already retried sources. |
| `pipeline.pause_demo` | REQUIRES_APPROVAL | Writes only a simulated pause effect marker. It does not change the pipeline or stop the worker. |
| Any unregistered action | DENY | No effect is executed. |

Policy is versioned as `m3-v1`. The SHA-256 payload digest binds schema version, tenant, requester, action, target, validated parameters, policy version and expiry. Approval stores that exact digest. Requester and approver membership and the current policy are checked again before the effect. One effect is keyed by proposal ID; retries from an expired execution lease reconcile an existing effect before another attempt. A unique source-run link bounds demo retry to one new run. Proposal and incident timelines and audit records contain fixed status codes, not credentials or raw worker logs.

## Limits and safe failure

The M3 approval and notification flows are local demonstrations. The local notification quota is policy-checked but is not a distributed rate limiter. Automatic action proposals, external notifications, production identity, a real pipeline pause, customer-system mutation and full recovery verification are outside this milestone. A `VERIFIED` retry confirms the new run was durably enqueued; it does not claim the retried pipeline succeeded. An inconclusive verification remains explicit and cannot resolve an incident.

The initial action schema downgrade removes action history and the retry link. Preserve volumes and apply a forward fix rather than downgrading a database with useful records.
