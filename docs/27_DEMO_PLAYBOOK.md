# Demonstration playbook: commands and expected evidence

These workflows are **design scenarios** until code and scripts are implemented. Never tell a viewer an example screenshot is actual observed data if seeded/simulated.

## D1 — Healthy order pipeline
Seed demo tenant, synthetic orders and a contract. Run one daily partition; inspect DB run, output Parquet/manifest, PASS quality and PUBLISHED publication; check audit and metrics.

## D2 — Transient source failure
Inject 503 for first two attempts only. Ensure transient classification, bounded attempts, eventual transform and recorded audit timeline. No unbounded worker retry.

## D3 — Persistent fault
Inject permanent source unavailable. Ensure run FAILED and incident OPEN after capped retries, plausible diagnosis but not confirmed cause, no auto-resolution.

## D4 — Silent data loss (signature)
Synthetic expected 150,000 orders, observed 105,000 after intentional row-drop. Processing status SUCCEEDED; quality FAIL; publication QUARANTINED. Inspect contract version, evidence and affected `RevenueDashboard` / `SalesForecast` demo assets through lineage.

## D5 — Guarded remediation (signature)
Diagnosis proposes bounded retry. Policy ALLOW only for safe demo transient class. Unsafe data deletion DENY. For replay demo, show exact scoped proposal, simulation results, authorized separate approver, action receipt and VERIFIED/INCONCLUSIVE outcome.

## D6 — Telemetry schema drift (advanced)
Synthetic stream schema v15 to v14 decoder causes DLQ growth and missing ClickHouse/Parquet records. Compare broker/source count and sink count; incident opens; isolate captured snapshot; shadow replay with new *pre-reviewed* decoder; approve optional bounded replay; verify reconciliation and uniqueness.

## D7 — Security negative journey
Login as tenant A viewer; attempt tenant B incident fetch and run/approval mutation, demonstrate 403/404 and no mutation; tampered proposal digest denied; injection text harmless; inspect audit evidence.

## Presentation narrative
1. Baseline green state with real local pipeline proof.
2. Inject hidden loss and see meaningful alarm (not just red exception).
3. Open incident, view evidence, derived blast radius, diagnosis with uncertainty.
4. Review policy and safe action; optional shadow lab compares invariants.
5. Execute only when approved, show independent post-action verification and audit.
6. Demonstrate a denial and cross-tenant test; show measured outcomes and current limits.

## Recording checklist
Fresh checkout and documented setup; no secrets; commands/logs/screens are reproducible; record local hardware, labels for synthetic data and limitations. Do not claim live Azure when showing mocked data.
