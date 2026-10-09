# Operational runbook (to adapt after services exist)

## Service down
Confirm environment/mode; inspect process and readiness, dependency reachability, redacted correlation-ID logs, last migration. Avoid blind restart mid-mutation. Record outage/impact and restart/rollback only when state can be reconciled.

## Queue or worker stuck
Inspect age/lease/status, Postgres transaction health, Redis availability, attempt budget. Don't requeue unverified external side effects. Reconcile action receipts before retries. Capture action/trace ID and resulting state.

## Repeated source/API errors
Classify transient (throttle/unavailable) vs nonretryable (permission/schema/invalid request). Check provider quota/error category, changes, source snapshot. Stop at retry limit, keep incident open and escalate.

## Data quality failure while run succeeds
Hold/quarantine output. Compare contract version and expected/observed counts, schema fingerprints, rejected rows and window. Inspect lineage impact. Require scoped waiver and audit if business owner accepts risk; never silently publish.

## Streaming lag and dead letters
Check partition lag trend, consumer health, checkpoints, poison message samples after sanitization, decoder version, source/sink reconciliation. Do not reset production offsets automatically. Replay only within authorized retained window, with dedupe.

## Agent/model unreachable
Mark diagnosis degraded. Deterministic checks, incidents, policy and pipeline continue. Do not bypass safety controls. Restore model optionally with bounded timeout and manual review.

## Security suspicion
Disable connector or local demo integration, rotate exposed credentials out of band, preserve sanitized evidence, examine audit and tenant scope, invalidate sessions, consult incident owner. Never copy secrets into tickets or model prompts.

## Recovery proof
Verify source/sink invariants and data contract after action. If incomplete, status INCONCLUSIVE and incident stays active; log follow-up owner and safe next step.
