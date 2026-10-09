# Incident detection, evidence and diagnosis

## Trigger sources
- Failed/timed-out execution and exhausted retry budget.
- Quality FAIL/WARN according to severity policy.
- Freshness SLO missed even though no run occurred.
- Streaming lag/DLQ/event-time lateness and mismatch between source and sink reconciliation.
- Suspicious configuration or unsafe proposal (security finding, not necessarily data incident).

## Incident record
Stable tenant ID, fingerprint, category, severity, lifecycle state, first/last seen, dedup count, affected assets, run/check refs, evidence references, owner, hypothesis revisions, proposed actions, resolution verification and timeline.

## Dedup and severity
Fingerprint combines tenant, asset or pipeline, failure-class, optional schema fingerprint or error code, and configured alert window. Dedup increments observations; allow reopen after recurrence. Severity is deterministic using asset criticality, affected scope, SLO breach and data validity; do not let free-form LLM text silently raise/lower priority.

## Evidence types
Typed log reference (redacted), failed task code, quality rule result, schema fingerprint/version, pipeline config/commit digest, metrics window, trace reference, source/sink reconciliation, operator note, change event. Evidence includes `collected_at`, producer, tenant scope, checksum where appropriate. Do not store raw PII or secrets. Mark ephemeral evidence that expired.

## Structured hypothesis
```json
{
  "summary": "Upstream schema change may have broken decoding",
  "category": "SCHEMA_INCOMPATIBILITY",
  "supporting_evidence_refs": ["evidence:schema-v8", "evidence:decoder-error-12"],
  "contradicting_evidence_refs": [],
  "confidence_label": "MEDIUM",
  "unknowns": ["Historical decoder compatibility not independently verified"],
  "next_checks": ["Replay captured event in isolated decoder fixture"],
  "status": "HYPOTHESIS"
}
```
`CONFIRMED` requires independent verification evidence; model confidence alone is insufficient.

## Incident workflow
OPEN → INVESTIGATING → ACTION_PROPOSED → (AWAITING_APPROVAL if needed) → MITIGATING → VERIFYING → RESOLVED. Also ACKNOWLEDGED, ESCALATED, REOPENED as explicit transitions. Failed/indeterminate verification must not resolve.

## Human experience
One timeline integrating events: detected, evidence collected, hypothesis evaluated, impact calculated, policy checked, proposal approved/denied, execution attempted, verification outcome and notes.

## Tests
No incident storms under repeated alerts; genuine distinct incidents not merged; missing evidence yields UNKNOWN; non-owner cannot mutate; downgrade severity requires authorized action/audit; unresolved after exhausted retries.
