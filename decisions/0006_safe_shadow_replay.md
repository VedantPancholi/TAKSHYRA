# ADR 0006 — Isolated shadow replay before selected repairs
**Status:** Proposed for R4 (2026-10-09)

**Decision intent:** Snapshot-specific, bounded local replay compares data correctness before live changes; never claim production safety from simulation alone. Prevent sandbox network writes and path escape.

**Tradeoffs:** Retained snapshots/storage cost, imperfect reproduction of external side effects, extra verification requirements. Implement only after policy/recovery core is proven.
