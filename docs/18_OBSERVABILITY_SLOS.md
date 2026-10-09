# Observability, reliability SLOs and audit discipline

## Monitoring strategy
OpenTelemetry traces/structured logs/counters for request → durable run record → queue → worker → quality → incident → agent → policy → action → verification. Do not use run IDs, user IDs, unbounded URLs or error strings as metrics labels (high cardinality). Propagate correlation and causation IDs through DB records and safe metadata.

## Proposed metrics
- `pipeline_runs_total{status,adapter}`; `pipeline_run_duration_seconds` histogram.
- `pipeline_records_total{direction}` where direction is read/written/rejected.
- `quality_checks_total{type,outcome}`; `datasets_publication_total{outcome}`.
- `incident_open_total{severity}`; `incident_detection_delay_seconds`.
- `action_executions_total{action_type,outcome}`; `action_verification_total{outcome}`.
- `worker_task_age_seconds`; `worker_retries_total{category}`; dead tasks.
- `agent_executions_total{agent_type,provider,outcome}`; latency and optional token estimate.
- Stream-specific lag, late event and reconciliation metrics as documented in 14.

## Alerts and SLOs
Start with **user-configurable** objectives, not advertised SaaS SLAs: dataset freshness, quality passing %, pipeline execution success %, queue age, incident acknowledgement time, MTTR. Define numerator, denominator, rolling window, suppression policy, missing-data behavior and evaluation cadence. SLO breach is only as reliable as collected evidence.

## Health probes
`/health/live` process alive, `/health/ready` critical dependencies ready; no stack traces or secrets. Degraded optional LLM/Azure should not necessarily render the local pipeline engine unavailable; show dependent feature as degraded explicitly.

## Logging requirements
Structured JSON: timestamp, service, severity, event name, tenant-scoped safe identifier, run_id, incident_id, correlation_id, error category, sanitized metadata. Filter common auth headers, URLs with tokens, connection strings and raw PII. Audit retained independently with separate access policy.

## Runbooks
Worker stuck; database unavailable; queue unavailable; non-retryable schema failure; destination partial write; repeated quality failure; optional AI/model offline; Azure rate limit; duplicate action/replay; suspected security incident; backup restore. Every runbook: symptoms, safe checks, authorized actions, escalation, evidence and resolution verification.

## UI clarity
Timestamp every chart, mark `last observed`, display stale telemetry, separate `unknown` from `healthy`, and identify demo/simulated metrics. Never substitute attractive static placeholders as real incident counts.
