# Codex M3 — safe action service, policy, approval and audit

Implement registered typed actions: `incident.annotate`, `notification.emit_local`, bounded `pipeline.retry_demo`, and simulated `pipeline.pause_demo` with explicit policy. Unlisted actions (shell/SQL/IAM/deletion/infrastructure) DENY always. Policy server-authoritative, action payload immutable, canonical hash, approval expiry, role separation, preconditions, audit events, execution leases and independent result verification.

**Tests:** tampered approval digest, expired request, self-approval high risk, lost approver role, wrong tenant, duplicate concurrent requests, retry limit, non-transient failure, unknown action. Confirm no disallowed effect happened. Demonstrate ALLOW, DENY and REQUIRES_APPROVAL through API, not only unit tests.

**Exit:** policy→approval→execution→verification timeline traceable end-to-end; negative tests pass; UI can come later. Re-read security spec before merging.
