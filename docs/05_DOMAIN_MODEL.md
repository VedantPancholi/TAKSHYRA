# Domain model, ownership and schema evolution

## Schema conventions
PostgreSQL + SQLAlchemy 2 + Alembic. IDs UUID. UTC timezone-aware timestamps. Tenant-owned unique constraints and indexes generally begin with `tenant_id`. Serialize configuration as validated, versioned JSON without secrets; actual secret values are references only. Enforce FK ownership, non-nullability, bounded text and valid enums. `created_by` is an authenticated subject, never trusted from request body.

## Iterative entity inventory
| Entity | Key fields (illustrative) | Consistency invariants | Release |
|---|---|---|---|
| Tenant | id, slug, status, created_at | slug unique | R1 |
| User | id, external_subject, email, status | externally authenticated subject unique per issuer | R1 |
| Membership | tenant_id, user_id, role, status | `(tenant_id,user_id)` unique | R1 |
| PipelineDefinition | tenant_id, id, name, version, config, owner, enabled | config validated; no executable arbitrary code | R1 |
| PipelineRun | id, tenant_id, pipeline_id, idempotency_key, payload_digest, execution_status, timestamps, publication_status | unique tenant+key+intent, valid state transitions | R1 |
| RunAttempt | run_id, number, lease_owner, lease_until, error_code, counts, result | unique run+attempt; bounded | R1 |
| Dataset | tenant_id, id, namespace, name, sensitivity, owner | unique normalized namespace/name/tenant | R2/R3 |
| DatasetVersion | dataset_id, schema_fingerprint, manifest_uri, checksum, window | immutable published version metadata | R3 |
| DataContract | tenant_id, id, dataset_id, owner, active_version | must have accountable owner | R3 |
| ContractVersion | contract_id, version, schema_rules, quality_rules, effective_at | immutable version, hash | R3 |
| QualityResult | run_id, dataset_id, rule_id, version, outcome, expected, observed, evidence_ref | outcome separated from execution status | R1/R3 |
| PublicationDecision | output_ref, run_id, status, reason, policy_version | no publish on strict failure | R3 |
| DataProduct | id, tenant_id, name, criticality, consumer_type, owner | trusted dependency mapping only | R3 |
| LineageEdge | src_asset, dest_asset, provenance, valid_from/to, observed_at | prevent cross-tenant edges; source type explicit | R3 |
| SLODefinition/Evaluation | asset, objective, window, observed, result | objective versioned and windowed | R3 |
| Incident | id, fingerprint, tenant, severity, category, lifecycle_status, opened_at, resolved_at | dedup window scoped by tenant | R2 |
| IncidentEvent/Evidence | incident, type, actor, safe payload/ref, checksum, timestamp | redaction; append-only events | R2 |
| AgentExecution | incident, provider, prompt_version, output schema_version, status, token/cost optional | provider not privileged | R2 |
| RemediationProposal | incident, action_type, canonical_payload, digest, policy_ref, expires_at | immutable payload after evaluation | R2 |
| PolicyDecision | proposal, policy_version, outcome, reason, evaluated_at | no client-supplied decision | R2 |
| Approval | proposal, approver, decision, payload_digest, expires_at | no self approval for high risk; exact payload match | R2 |
| ActionExecution | proposal, idempotency, lease, status, actor, result | one authorized bounded attempt per execution key | R2 |
| VerificationResult | action, invariant_results, outcome, evidence_refs | separate execution success vs verified success | R2/R4 |
| ReplaySession | snapshot_ref, action_ref, isolation_ref, input/output manifests, outcome | never changes production data | R4 |
| KnowledgeRecord | tenant, incident, verified_root_cause, successful_resolution, tags, validated_by | provisional versus verified distinction | R4 |
| ChangeEvent | target, actor, version, type, safe diff, time | provenance captured | R3 |
| AuditEvent | tenant, actor, action, target, result, correlation_id, time, sanitized_fields | append-only app API; service privileged delete disabled | R1/R2 |

## Isolation strategy
An initial database per deployment with tenant_id-scoped repository methods; central policy layer; authorization tests for all routes. Consider Postgres RLS as **defense-in-depth** when implementation can correctly establish tenant-scoped DB context. RLS is not a substitute for permission checks and must be tested against connection pool context leakage.

## Sensitive data
Store checksums and aggregates rather than unnecessary raw rows. Redact endpoint strings/SQL. Design retention and data export per tenant. Treat incident evidence as sensitive by default. See `docs/30_PRIVACY_AND_RETENTION.md`.

## Migration discipline
Only forward migrations committed with feature code. Test upgrade on fresh DB and seeded pre-upgrade state when relevant; document downgrade or compensating forward migration plan for nonreversible changes. Avoid automatic `create_all()` on production startup.
