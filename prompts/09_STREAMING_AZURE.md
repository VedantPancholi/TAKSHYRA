# Codex M9 — streaming fault fixtures + optional Azure sandbox

First implement synthetic stream events, consumer lag/DLQ/checkpoint metrics, schema drift v14→v15, duplicate/out-of-order/late messages and source→sink reconciliation with at-least-once semantics. Provide optional Compose streaming profile if resources permit. Test a committed offset with missing sink writes is detected.

Then implement ADF run-state **read-only** connector and Azure Monitor query interface against mocked clients; optional Event Hubs sandbox reader with separate group and checkpoint documentation. Never auto-provision resources. Any live Azure test is opt-in after separate sandbox identity/allowlist/budget/cleanup review. No unknown Fabric API inventions.

**Tests:** bounded polling, paging, throttling, least privilege, token/redaction, tenant scoped resource IDs, retention/replay denial, poison messages, mock/live labels.

**Exit:** deterministic local streaming incident end-to-end and mocked Azure tests; if no Azure access, label live integration NOT VERIFIED (not a blocker to local demo).
