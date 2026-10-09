# Policy engine, authorization, approvals and action registry

## Policy result
`ALLOW | DENY | REQUIRES_APPROVAL`, with `policy_id/version`, reason codes, risk class, actor, target scope and evaluated time. Policy must be deterministic and separate from LLM. Re-check policy and principal rights immediately before action execution.

## Initial typed action catalog
| Action | Default policy (local demo only) | Preconditions / constraints |
|---|---|---|
| `incident.annotate` | ALLOW to authorized editor | sanitized text, idempotent event |
| `notification.emit_local` | ALLOW | local sink, rate-limited |
| `pipeline.retry_demo` | ALLOW under strict limits; otherwise approval | transient failure only; max attempts and fixed run |
| `pipeline.pause_demo` | REQUIRES_APPROVAL | exact pipeline state/version and expiry |
| `pipeline.replay_demo_window` | REQUIRES_APPROVAL | retention/snapshot exists, isolation proof, exact bounded window |
| `data.quarantine_demo` | REQUIRES_APPROVAL or explicit operator only | output version bound; no deletion |
| arbitrary shell/SQL/Python/cloud command | DENY | never implement raw execution endpoint |
| IAM/network/delete/deploy/infrastructure mutation | DENY in current project | no approval bypass |

## Canonical payload / approval binding
Derive SHA-256 from canonical representation of action schema version, tenant identity, target, bounded input, preconditions, relevant policy/version and expiration. Use deterministic canonical serialization. Any changed payload, new principal risk, or scope invalidates old approval. Human approver receives both human summary and machine-precise exact action. Requester must not approve own high-risk proposal. Approval expires, one-time execution claim enforced.

## Safety checks
- Authenticated actor + permission + tenant membership.
- Action type is registered and supported by target adapter.
- Parameters validated against strict schema; unexpected keys forbidden.
- Target existence/version, environment allowlist and source data authority.
- Risk determined server-side; no agent/client bypass.
- Idempotency key, attempt budget, rate-limit, execution deadline and lease.
- Audit decision and attempt transactionally; record terminal verification outcome.
- No optimistic automatic retry for non-idempotent action without reconciled execution evidence.

## Action lifecycle and failure
`proposal -> policy -> [approval] -> precondition guard -> leased EXECUTING -> EXECUTED/FAILED -> VERIFYING -> VERIFIED/INCONCLUSIVE/FAILED`. If worker dies after calling external adapter but before persisting result, reconcile external action via idempotency/operation ID; **do not blindly repeat** potentially non-idempotent operation.

## Policy tests (mandatory)
Unknown action DENY; actor changed role before execution DENY; cross-tenant DENY; self-approval DENY; expiry DENY; payload tamper DENY; duplicate request no duplicate effect; retry budget exhausted DENY; dangerous prompt-injection content is inert; missing reliable verification results INCONCLUSIVE; approval from one tenant cannot authorize another.
