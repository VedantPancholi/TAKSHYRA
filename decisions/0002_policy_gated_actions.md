# ADR 0002 — Policy and approval before mutation
**Status:** Accepted as initial design (2026-10-09)

**Context:** LLM outputs can hallucinate or be manipulated by input data; broad tools can corrupt data or infrastructure.

**Decision:** Agents only produce structured proposals; server authorization + deterministic policy + immutable payload binding + scoped approval + allowlisted executor + verification + audit. Unknown destructive actions deny.

**Tradeoffs:** Less dramatic autonomy but safer auditable capabilities. New actions require schemas, policy, tests and explicit risk review.
