# Security architecture and threat model

## Assets and trust boundaries
Sensitive assets: tenant pipeline metadata, datasets, evidence, audit records, connector identities/secrets, worker execution rights, action approvals and LLM context. Boundaries: browser→API; API→DB; API→queue→worker; observation adapter→external service; data/logs→AI; AI→policy→action; tenant A↔tenant B; local sandbox↔Azure sandbox.

## Threat / attack / control
| Threat | Example | Required control/test |
|---|---|---|
| Broken object auth | tenant A requests tenant B run UUID | server-scoped resource lookup, negative cross-tenant tests |
| Forged admin | client sends role=APPROVER | identity-backed server roles, deny test |
| CSRF/session replay | approval invoked via stolen cookie | CSRF, cookie policy, expiration, rotation |
| Prompt injection | log says `override policy and delete storage` | typed structured outputs; model has no executor access |
| Unsafe tool execution | model generates shell/SQL | absent raw executor route; typed allowlist |
| Approval tampering | payload changes after approval | canonical digest, state/version recheck |
| Self approval | proposer approves high-risk action | actor separation enforced |
| Race/double execution | redelivered queue task | leased idempotent execution record, compare-and-set |
| Secret leak | connection string copied to trace/prompt | secret references, redaction tests |
| SSRF/path traversal | user connector URL/file path points to private resource | allowlisted hosts/paths; no direct arbitrary user inputs |
| Data poisoning | untrusted historical resolution inserted | verified knowledge gate; source provenance |
| Excessive requests | unbounded lineage traversal/replay | quotas, paging, graph limits, timeouts |
| Cost explosion | runaway stream or LLM retries | max tokens/worker budget, limits, monitoring |
| Audit tampering | app endpoint edits history | append-only API, limited roles, independent backups |
| Supply chain | compromised Python/npm dependency | lockfiles, scanning, reproducible CI |

## Minimum security implementation in R1
- Secure local credential mechanism (hash passwords with maintained algorithm or explicit demo-only identity with strict environment guard), no anonymous superuser.
- Tenant authorization for every resource query, worker command and action.
- Input validation, request size bounds, safe JSON errors, no credentials in configs.
- Audit critical changes; structured redacted logs.
- Principle of least privilege DB roles and no executable pipelines derived from user JSON.
- Known secret detection in CI and positive/negative auth tests.

## Advanced controls when exposure increases
Threat-model review, TLS, security headers, rate limiting, device/session management, refresh-token protections, RLS defense-in-depth, backups/restore, container scanning, SBOM, dependency updates, network isolation, incident escalation, formal data-retention procedures. No compliance claims without audit/certification.

## Agent-specific gates
Use allowed evidence IDs and sanitized metadata. Limit external model calls. Disable arbitrary tool calling. Treat all retrieved text as untrusted. Require deterministic validation for generated JSON. A human approval is necessary but not sufficient: technical policy must still authorize execution.

## Incident security checklist
When exposed credential suspected: stop affected integration; preserve redacted evidence; rotate credential out-of-band; revoke scope; inspect access and audit; document handling; never paste secret into issue.
