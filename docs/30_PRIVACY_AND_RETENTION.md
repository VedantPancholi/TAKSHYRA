# Data minimization, retention and privacy design

## Default posture
Run with synthetic data. Collect metadata and aggregates rather than copying raw source rows, secrets or full production SQL. A connector must explicitly declare which evidence types it is authorized to ingest. No hidden third-party analytics or model calls.

## Data classification
- Public: product docs and sanitized demo metrics.
- Internal: pipeline names/config metadata, run IDs, metrics, incident timelines.
- Confidential: dataset schemas, source endpoint topology, lineage, deployment diffs.
- Restricted: access tokens, secrets, raw records/PII, credentials (never persisted in incident/LLM context).

## Retention (proposal; configurable in implementation)
| Data | Starting demo policy | Notes |
|---|---|---|
| Pipeline run metadata | 90 days | retention can be tuned per tenant |
| Logs/traces | 14 days | sanitize, cap volume |
| Incident evidence | 90 days | references may expire and show missing |
| Shadow input snapshots | 7 days | synthetic data only; explicit cleanup |
| Audit metadata | 180 days | scoped; legal needs may differ |
| Incident memory | review every 90 days | verified vs provisional, staleness flags |

These are **design defaults**, not an implemented retention mechanism or legal compliance recommendation.

## Required controls
Per-tenant export and deletion plan consistent with audit/legal retention; purpose limitation; consent/notice if required; incident artifact access policy; secret redaction across outputs/model prompts; deletion jobs with proof logs; backup expiration, access and restore tests. Do not promise full deletion until backups/third-party copies are understood.
