# HTTP API contract (planned)

Implemented M1 routes are documented in [37_M1_LOCAL_CORE.md](37_M1_LOCAL_CORE.md), and M2 incident routes in [38_M2_INCIDENTS.md](38_M2_INCIDENTS.md). The remaining routes and global conventions below are future targets; do not infer current behavior from this planned contract.

## Global conventions
- Prefix `/api/v1`. Typed OpenAPI models. JSON. UUID IDs. ISO-8601 UTC timestamps.
- Auth via validated local development login for demo, replaceable OIDC/Entra. No header-only forged admin or public seeded bypass.
- Tenant is derived from authenticated scoped membership/context. If tenant routing is specified in URL it must be authorized; never accept unsupervised tenant selection.
- Collection endpoints paginated, bounded page sizes (default 25, max 100), filter/sort allowlists.
- CSRF protection for cookie sessions; secure cookie controls; bearer OIDC flows later. Rate limits and max request sizes.
- For mutating POST: idempotency key in header and payload digest checks where appropriate.
- Error envelope: `{ "error": { "code": "STRING", "message": "Safe description", "correlation_id": "UUID", "details": [] } }`.
- Consistent `403` for authorized role lack of permission; `404` for hidden cross-tenant object where appropriate. Don't leak object existence.

## Resource operations and minimum permissions
| Method/route | Purpose | Permission |
|---|---|---|
| `GET /health/live`, `/health/ready` | local/service health | no secret details |
| `GET /api/v1/me` | session and role | authenticated |
| `GET/POST /api/v1/pipelines` | list/create definitions | view / pipeline.manage |
| `GET/PATCH /api/v1/pipelines/{id}` | inspect/update | view / pipeline.manage |
| `POST /api/v1/pipelines/{id}/runs` | enqueue idempotently | pipeline.execute |
| `GET /api/v1/runs/{id}` | run/attempt/quality summary | pipeline.view |
| `GET /api/v1/datasets`, `/{id}` | assets and versions | asset.view |
| `GET/POST /api/v1/contracts` | active/versioned contract | contract.view / contract.manage |
| `GET /api/v1/lineage/{asset_id}/impact` | bounded graph traversal | asset.view |
| `GET /api/v1/incidents`, `/{id}` | incidents/evidence | incident.view |
| `PATCH /api/v1/incidents/{id}` | mark open incident investigating | executor and owner checks |
| `POST /api/v1/demo/pipelines/{id}/freshness-miss` | simulated F07 event with no run | development executor only |
| `GET /api/v1/incidents/{id}/timeline` | immutable-style lifecycle | incident.view |
| `POST /api/v1/incidents/{id}/diagnoses` | launch bounded investigation | incident.investigate |
| `GET /api/v1/proposals/{id}` | inspect exact plan and policy | proposal.view |
| `POST /api/v1/proposals/{id}/approve` | approve exact immutable payload | proposal.approve |
| `POST /api/v1/proposals/{id}/reject` | reject proposal | proposal.approve |
| `POST /api/v1/proposals/{id}/execute` | policy-gated action | action.execute |
| `GET /api/v1/actions/{id}/verification` | post-action outcome | action.view |
| `GET/POST /api/v1/replays` | local-only shadow simulation | replay.view / replay.simulate |
| `GET /api/v1/audit-events` | tenant-scoped audit | audit.view |
| `POST /api/v1/demo/scenarios/{name}` | inject bounded demo scenario | development-only + demo.manage |

The incident list/detail routes and the two added M2 routes above are implemented. The separate timeline and diagnosis routes, generic demo scenario route, and other resource operations remain planned. M2 timeline events are embedded in `GET /api/v1/incidents/{id}`. M2 run trigger accepts only `{}`, `{"parameters":{}}` or one of the fixed `demo_fault` codes `F02`, `F03`, `F04`; the header holds the `Idempotency-Key`. The illustrative trigger below is a future contract and is not accepted by the M2 API.

## Example trigger (illustrative)
```json
{
  "idempotency_key": "orders-2026-10-09-t1-a",
  "parameters": {"window_start": "2026-10-08T00:00:00Z", "window_end": "2026-10-09T00:00:00Z"}
}
```
Request must not accept direct filesystem paths, shell commands or arbitrary SQL.

## Example remediation proposal (server-created)
```json
{
  "proposal_id": "00000000-0000-4000-8000-000000000001",
  "action_type": "pipeline.retry_demo",
  "action_schema_version": 1,
  "target_pipeline_id": "00000000-0000-4000-8000-000000000002",
  "scope": {"run_id": "00000000-0000-4000-8000-000000000003"},
  "parameters": {"max_attempts": 1},
  "preconditions": ["source_classification_is_transient"],
  "risk_level": "LOW",
  "evidence_refs": ["incident-evidence:example"],
  "expires_at": "2026-10-10T00:00:00Z"
}
```
The **server** supplies policy, digest, risk, tenant context, and expiry. Example UUIDs and dates are fictional.

## API definition of done
Document request/response models, role matrix, sample 401/403/404/409/422/429 behaviors, 202 async receipt and polling, pagination, and trace IDs in generated docs; test with real requests, not just schema imports.
