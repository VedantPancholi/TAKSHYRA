# Acceptance gates, definition of done and release controls

## Feature completion checklist
- [ ] Business requirement and testable acceptance criteria documented.
- [ ] Real code integrated; not only interfaces, docs, mocks, decorative UI or TODOs.
- [ ] Database migration and reset/seed path verified where needed.
- [ ] Input schema validation; safe errors; pagination, limits and idempotency as needed.
- [ ] Tenant and permission checks on API, service, worker and artifact references.
- [ ] Unit/integration/negative test cases pass (actual commands recorded).
- [ ] Failure/timeout/retry behavior is bounded, observable, tested.
- [ ] Audit and state transitions correct for mutations.
- [ ] Operational logs/metrics and uncertainty/real-vs-simulated labels added.
- [ ] API/UI and setup documentation match working behavior.
- [ ] No unreviewed secrets or privileged cloud actions introduced.
- [ ] CI updated to test new functionality without false green placeholders.

## Mandatory security gates before action execution
RBAC, tenant isolation, action registry validation, canonical payload approval binding, expiration, no self-approval high risk, lease/idempotency, deterministic policy, safe adapter capability, verifier and audit. If one is unavailable, fail closed and show blocker.

## Repository rules
No TODO-only Makefile targets that succeed; no CI scripts that silently skip required application tests after they exist; no success badges without actual checks; no unlimited LLM/worker retries; no unchecked external links or arbitrary connector hosts; no demo credentials valid in production mode.

## Release decision
Maintain a checklist of known risk, dependencies, unsupported integrations, failed tests, restore results, limitations, cost and security review. A portfolio release can be marked **demo-ready**, not **enterprise certified**.
