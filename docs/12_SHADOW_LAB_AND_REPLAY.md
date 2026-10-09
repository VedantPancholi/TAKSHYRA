# Shadow Recovery Lab, Time Machine and safe replay

## Purpose
Test a narrowly defined remediation using an isolated snapshot before trying a live change. Reproduce incident evidence and compare corrected output under known assumptions. A green simulation **does not guarantee** live production success.

## Scope for first implementation (R4)
- Synthetic local CSV/Parquet input snapshot with digest and manifest.
- Replay a bounded partition/time window using versioned pipeline configuration.
- Run the proposed deterministic transform in a separate scratch namespace, filesystem, and tenant-scoped sandbox.
- Prevent sandbox workers from accessing production endpoints or secrets.
- Compare input/output row counts, rejected counts, keys, checksums, schema, duplicate rate, quality contract and runtime.
- Emit report: `SUPPORTED | PARTIAL | IMPOSSIBLE` plus reasons, input snapshot availability and results.

## Replay protocol
1. Choose incident and exact source snapshot/time window.
2. Check permission to read snapshot and retention coverage; record snapshot checksum/config/image version.
3. Reserve bounded isolated storage/compute and reject uncontrolled external/network writes.
4. Execute capped replay; collect output manifest and quality results.
5. Compare with baseline and expected invariant, save report; do not auto-approve live action.
6. Generate proposal scoped to exact source, version, affected partitions and dedupe strategy.
7. Policy/approval/execution/verification remain separate steps.

## Time Machine query
`GET incident history -> show run attempts + schema/config/version/quality lineage timeline -> optionally start sandbox replay from retained artifacts`.

## Streaming replay restrictions
Only replay if broker retention or authorized captured snapshot covers full requested offsets/window. Partition-specific offsets, consumer group and checkpoint state must be recorded. Use isolated consumer group, idempotent sink writes and dedupe keys; never reset existing production consumer-group offsets from an agent.

## Limitations and negative cases
External API side effects cannot necessarily be simulated; corrupted/incomplete snapshot means PARTIAL, not PASS; concurrency differs in sandbox; cost may differ; unknown schema compatibility must be verified. Test window outside retention, changed source snapshot digest, schema mismatch, sandbox file traversal, resource exhaustion, malicious event text, duplicate replays, output mismatch.
