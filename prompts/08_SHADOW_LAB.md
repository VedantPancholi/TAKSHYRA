# Codex M8 — Shadow Recovery Lab and Time Machine

Create isolated snapshot store and ReplaySession for synthetic local files. Support one narrowly scoped recovery simulation (e.g. replay missing orders window) and independently compare staged output to contract invariants; save before/after manifests, checksums, configuration version, retention/coverage and execution receipt. Show `SUPPORTED`, `PARTIAL`, `IMPOSSIBLE` truthfully.

**Security:** sandbox cannot access production endpoints or secrets; path allowlist; user authorization; bounded CPU/time/storage; safe cleanup; replay never changes published source/destination directly. Action remains subject to policy and approval after a successful simulation.

**Tests:** missing/expired snapshot, malicious path, duplicate event, corrupted snapshot, partial coverage, changed manifest digest, worker abort, INCONCLUSIVE verification, unauthorized replay and repeated action idempotency.

**Exit:** reproducible isolated replay, comparison report, post-action verification tied to incident; no claim that sandbox simulation proves production safety.
