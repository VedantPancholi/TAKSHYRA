# M8 local shadow replay and recovery verification

M8 supports one bounded recovery scenario: the seeded orders pipeline produces a quality incident after the `F04` row drop fault. It does not connect to or change Azure, AWS, or customer systems.

## Local demo

1. Start the stack using [local development](22_LOCAL_DEV.md), sign in as `demo-a-executor`, and click **Create row deficit run**. Refresh and select the new `QUALITY_SOURCE_ROW_COUNT_MATCH` incident after the worker finishes.
2. Click **Run shadow replay**. The API copies the fixed source into a temporary directory, replays the run with its bound contract, compares the baseline and replay, and removes the scratch files. `SUPPORTED` means the local replay restored the row count and publication checks. `PARTIAL` or `IMPOSSIBLE` does not authorize recovery.
3. Select **Reprocess row deficit**, evaluate the proposal, and inspect the report ID, target run and payload digest. Sign in as `demo-a-approver` and approve the exact proposal. Return to the original executor account and execute it. This queues a new local run; action verification here means durable enqueue only.
4. Wait for the worker, then click **Verify recovered data**. The API independently reads the recovery run and its manifest, checks the bound contract, source digest, row count, all persisted quality results and publication state. Only `VERIFIED` resolves the incident. A pending run returns `INCONCLUSIVE`; failed invariants return `FAILED` and leave the incident open.

The same flow is available through `POST /api/v1/incidents/{id}/shadow-replays`, `POST /api/v1/action-proposals` with `pipeline.reprocess_demo`, existing approval and execute routes, and `POST /api/v1/action-proposals/{id}/verify-recovery`. Corresponding GET routes list replays and read the recovery outcome. The console does not require a manually entered proposal ID.

## Security and limits

The replay is tenant scoped and bounded to the local fixture and bound contract. It uses temporary storage in the API container's output volume; it is a scratch replay, not a separate security sandbox. Reprocessing requires an executor and a different approver, and policy rechecks the source and report before execution. The report supports an observed repair path, not a confirmed root cause. Verified outcomes can appear as prior cases for later incidents with the same error code in the same tenant; those cases do not assert that the later incident has the same cause.

Only `F04` row deficit on `seed_orders_v1` has a recovery action. M8 has no generic pipeline repair, source code modification, provider credentials, Azure/AWS adapters, live production remediation, or new pipeline designer.

## How cloud integration would be tested

The next provider milestone needs a shared, tenant scoped connector contract and separate adapters. First validate read only collection of pipeline runs, logs, quality evidence and lineage against provider mocks. Then test in a customer approved sandbox using a dedicated identity with the minimum read permissions. A write action needs its own provider specific allowlist, exact target and parameters, approval, idempotency and a post action read back. Azure and AWS each require their own integration tests because their pipeline services and identity models differ. No live provider connection is required to verify M8.

For a company needing a new pipeline, capture source, destination, schedule, transform, contract, quality and acceptance requirements first. Build and deploy that pipeline in the company's chosen orchestrator under a separate project scope. Onboard its runs, checks and lineage into TAKSHYRA through the same connector contract. A general purpose pipeline designer and arbitrary pipeline generation are beyond the current milestone roadmap.
