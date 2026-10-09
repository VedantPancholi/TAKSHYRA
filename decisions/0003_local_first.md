# ADR 0003 — Local-first adapters and synthetic data
**Status:** Accepted as initial design (2026-10-09)

**Decision:** Offline local test/demo is the primary development environment. Azure/hosted LLM/streaming services are optional adapters with mocks and opt-in live sandbox tests. No auto cloud provisioning.

**Tradeoffs:** Local simulation cannot prove cloud behavior; document capability mismatches. Enables broad contribution without spend or sensitive data.
