# ADR 0004 — Separate execution, quality and publication state
**Status:** Accepted as initial design (2026-10-09)

**Decision:** Model execution, output quality and downstream visibility as independent axes. A compute-successful run can be quality-failed and quarantined.

**Tradeoffs:** More transitions and UX complexity; prevents silent data loss being classified as healthy. Add migration/compatibility tests when statuses evolve.
