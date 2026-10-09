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
