# State machines, event model and consistency protocol

## Distinct status axes
- `execution_status`: QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED, TIMED_OUT.
- `quality_status`: PENDING, PASS, WARN, FAIL, UNKNOWN.
- `publication_status`: HELD, PUBLISHED, QUARANTINED, REJECTED.

A successfully executed transform may be quality FAIL and publication QUARANTINED. Never collapse all three into a single `success` boolean.

## Pipeline run transitions
```text
QUEUED -> RUNNING -> {SUCCEEDED,FAILED,CANCELLED,TIMED_OUT}
QUEUED -> CANCELLED
```
Transitions update inside transactions using optimistic version/compare-and-set. A crashed worker lease may be reclaimed only after expiry and with a new bounded attempt. A final run must not become running again merely due to duplicate queue delivery; explicit retry creates a new attempt or new run according to documented semantics.

## Recovery proposal lifecycle
```text
PROPOSED -> POLICY_DENIED (terminal)
PROPOSED -> APPROVAL_PENDING -> {APPROVAL_DENIED, APPROVAL_EXPIRED, APPROVED}
PROPOSED -> POLICY_ALLOWED
{APPROVED,POLICY_ALLOWED} -> PRECONDITION_CHECK -> EXECUTING -> VERIFYING
VERIFYING -> {VERIFIED,FAILED,INCONCLUSIVE}
```
- No execution if approval expires, action digest changes, authorization changes, or target state no longer matches.
- `INCONCLUSIVE` is not auto-resolved. Execution success does not imply recovery success.
- Policy can explicitly deny a previously approved proposal upon re-evaluation.

## Typed domain events
Use versioned envelope: `event_id UUID`, `event_type`, `schema_version`, `tenant_id`, `subject_type/id`, `occurred_at UTC`, `observed_at UTC`, `correlation_id`, `causation_id`, `producer`, `safe_payload`. UUID identity guards re-delivery. Store outbox with transactional state change if queue relay durability is required; otherwise document unavoidable failure gap and recover on scan.

Examples: `pipeline.run.queued.v1`, `pipeline.attempt.started.v1`, `pipeline.run.finished.v1`, `quality.check.completed.v1`, `dataset.publication.held.v1`, `incident.opened.v1`, `proposal.created.v1`, `policy.evaluated.v1`, `approval.decided.v1`, `action.executed.v1`, `recovery.verified.v1`.

## Deduplication and ordering
- Dedup by `(tenant_id, event_id)` for observed messages and stable incident fingerprint+window for noisy alerts.
- Idempotency key reuse with different canonical request payload → HTTP 409.
- Timestamps alone do not provide globally causal ordering; use entity sequence/version plus correlation/causation links.
- Kafka/Event Hubs can reorder across partitions; never assume total order.
- Record raw/source timestamp, ingest timestamp and check timestamp separately.

## Audit ≠ logs
Audit is durable actor/action evidence; logs are operational diagnostics. Redact content and avoid using logs as sole audit store. Append-only at application layer is not cryptographic immutability; do not claim tamper-proof without immutable backing or signed/hash-chained records and threat review.
