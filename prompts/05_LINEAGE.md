# Codex M5 — asset registry, OpenLineage and impact

Implement tenant-scoped Dataset/DataProduct/consumer assets, owners, criticality, typed lineage edges, event parser for OpenLineage-compatible event fixtures (proper run/job/dataset identities), graph traversals with depth/node limits, declared vs observed vs inferred provenance, validity windows and impact API.

Seed graph: raw.orders → curated.orders → revenue dashboard and forecast model; telemetry raw → decoded → operations dashboard. Inject quality incident and list potential downstream consumers with path evidence. Never claim probable impact is confirmed corruption.

**Tests:** ingest event idempotently; no false cross-product edges when job lineage facet gives explicit mappings; cycles handled; traversal limits/partial flag; stale edge; cross-tenant isolation; unknown data gives unknown impact.

**Exit:** graph and impact API reflect real metadata and work with M4 incident, tests run, docs updated.
