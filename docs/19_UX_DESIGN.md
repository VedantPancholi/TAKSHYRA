# UX, information architecture and accessibility

## Product design goals
An operations console optimized for engineers under incident pressure: scan first, understand evidence second, act only after review. Clear typography, compact data tables, powerful filters, useful empty/error/loading states, keyboard accessible controls, safe color semantics and mobile-safe layouts.

## Navigation
1. **Overview** — pipeline health axes, incidents, at-risk assets, freshness/SLOs, activity.
2. **Pipelines & Runs** — registry, last run, attempts, execution/quality/publication badges, output manifest, logs.
3. **Data Assets** — dataset/data product registry, trust passport, contracts, ownership.
4. **Lineage** — graph with declared/observed/inferred edges, time scope, bounded impact list.
5. **Incident Center** — severity, owner, dedup count, linked evidence, timeline, hypotheses.
6. **Recovery Workbench** — proposal, expected effect, exact payload diff, policy, approval/denial and verification status.
7. **Shadow Lab** — available snapshot/replay, before/after metrics, incomplete simulation warnings.
8. **Streaming** — consumer lag, DLQ, source/sink reconciliation, partitions, late data (later).
9. **Audit & Governance** — filterable audit, policy versions, approval records; read-only as appropriate.
10. **Connectors & Settings** — health/capabilities/mode, resource allowlists, roles, demo scenario controls in development only.

## Signature incident detail page
- Header: incident code, severity, state, owner, last updated, affected pipeline.
- Tabs: Timeline | Evidence | Root-cause hypotheses | Blast Radius | Actions | Recovery Proof.
- Evidence cards link to exact checks/log references; show verified, provisional and unavailable.
- Recovery proposal displays `ALLOW / DENY / REQUIRES_APPROVAL`, exact scope/expiry, simulated comparison, approver identity, risk and one-click ability to **view** audit trail.
- Approve button only for authorized role and action; display changes since approval; require confirmation for high impact.

## Badges & semantics
Use multiple dimensions: execution green/red/gray, quality green/amber/red/unknown, publication held/published/quarantined/rejected. Colors are supplementary to text and icons; do not use a single confusing aggregate `healthy` field.

## Empty/error/slow states
No pipelines → guide to seed; no evidence → mark unknown; API unavailable → retry without losing edits; connector blocked → show mode/permission limitations; model offline → show deterministic fallback; pagination and graph traversal truncation warnings.

## Design system
Next.js + TypeScript, accessible component toolkit, keyboard/focus handling, contrast checks, UTC + user localized display, sticky column headers in incident grids, semantic charts with table fallback, reduced motion support. No fake dashboard numbers outside labeled demo mode.

## Recommended console redesign after M9

**Implementation note (2026-11-18):** The console now has distinct Overview, Incidents, Pipelines, Streaming and Governed actions routes. A persistent sidebar and shared in-memory workspace state support navigation and the incident-to-proposal handoff. The Pipelines page shows the current API registry and linked incidents; detailed run history and cloud controls remain future work.

The earlier single scrolling page proved the workflow but made the operator scan too much. The next design iteration should add Assets and Integrations when their APIs are ready, and move incident details to a dedicated route while preserving the queue's filters and scroll position. Keep tenant, environment and connector mode visible in the header as those capabilities become available.

1. **Find work quickly:** Add search, status/severity/owner/source filters, saved views such as *Needs me* and *Awaiting approval*, sortable columns and pagination. Keep primary actions in the table toolbar and details in the selected row or detail view. This follows [Carbon's data table guidance](https://v10.carbondesignsystem.com/components/data-table/usage/).
2. **Explain the problem in one screen:** The incident header shows one sentence in plain language, current status, owner, age, execution/quality/publication as separate states, and a clearly marked *simulated* or *observed* source. Put evidence, timeline, impact and recovery in tabs. Datadog's [incident detail](https://docs.datadoghq.com/incident_response/incident_management/investigate/) and [timeline](https://docs.datadoghq.com/incident_response/incident_management/investigate/timeline/) are useful patterns for this flow.
3. **Show data movement and trust:** A pipeline detail view should show source → transform → destination, latest run and quality result, freshness, owner, contract and downstream assets. Use a compact graph plus a readable list. dbt's [Catalog source page](https://docs.getdbt.com/docs/explore/explore-projects) combines lineage and freshness in context; Datadog's [pipeline monitoring](https://docs.datadoghq.com/observability_pipelines/monitoring_and_troubleshooting/monitoring_pipelines/) shows component-level throughput and errors.
4. **Make actions safe and legible:** The action panel states proposed effect, target, evidence, policy reason, required approver and expiry before the button. After execution, show a separate verification result. Keep developer IDs and payload digests under an expandable technical-details section.
5. **Use time and status consistently:** Put a time-range control on overview charts, and annotate changes such as incidents, approvals and recovery on run/quality graphs. Grafana's [alert state history](https://grafana.com/docs/grafana/latest/alerting/monitor-status/view-alert-state-history/) and [annotations](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/annotate-visualizations/) are useful references. Use text and icons with color, and offer dark and light themes.

Implement the navigation and incident queue first, the incident detail second, and the pipeline/asset pages third. Test these flows with an executor, approver and viewer using the same seeded scenarios; measure time to find an incident, identify evidence and complete an approved action. The final visual design should be reviewed with users before replacing the current console.
