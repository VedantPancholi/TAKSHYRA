# M7 diagnosis, first slice

This branch begins M7 with persisted, evidence-linked, deterministic hypotheses. It does not claim a verified root cause or alter policy and action authority.

## Local API and console

- `GET /api/v1/incidents/{id}/diagnoses` returns up to 20 recent revisions for a tenant member.
- `POST /api/v1/incidents/{id}/diagnoses` lets an executor generate a diagnosis from the current incident, run and quality records. It accepts no client-supplied evidence or free-form instructions. An assigned incident can only be diagnosed by its owner.
- A matching evidence snapshot returns the existing diagnosis. A changed incident observation or run/check state creates a new record.
- The operations console shows the latest diagnosis and a **Generate diagnosis** button for executors.

Rules currently cover row deficits, simulated freshness misses and source read failures. Each result is marked `HYPOTHESIS`, cites stored evidence IDs and lists unknowns and a next check. Unmatched evidence yields `UNKNOWN` with no invented cause. The method is recorded as `RULES_V1`.

## M7 work still ahead

- Add a bounded, explicitly opted-in local model provider. Validate its structured output and evidence references; fall back to rules on timeout, invalid output or absence.
- Add tenant-scoped incident memory only from independently verified outcomes. There are no verified resolution records yet, so memory must remain empty until that evidence exists.
- Evaluate diagnosis fixtures, including missing evidence and adversarial text. Keep model output advisory and policy decisions deterministic.

Do not present these hypotheses as confirmed causes. The demo pipeline and its faults remain synthetic.
