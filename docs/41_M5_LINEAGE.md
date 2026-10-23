# M5 asset graph and potential impact

M5 adds a tenant-scoped asset registry, directed lineage edges, recorded event identities and bounded downstream traversal. Migration `0006_lineage` creates `assets`, `lineage_edges` and `lineage_events`, and links the fixed orders pipeline to its curated output asset. Seeding creates two isolated simulated dependency chains per tenant: orders raw → curated → revenue dashboard/sales forecast, and telemetry raw → decoded → operations dashboard.

## API

Development Basic authentication and `X-Tenant-Slug` remain required. Tenant members may use:

- `GET /api/v1/assets` (first 100 sorted assets) and `GET /api/v1/assets/{id}`.
- `GET /api/v1/lineage/{asset_id}/impact?max_depth=4&node_limit=100[&as_of=...]`.
- `GET /api/v1/incidents/{incident_id}/impact?max_depth=4&node_limit=100`.

`max_depth` is 1–8 and `node_limit` is 2–500, counting the source. Traversal follows active tenant edges, stops on cycles, and returns `truncated=true` when a limit hides reachable nodes. Each downstream item includes path asset IDs, edge IDs, origins, source labels, owner and criticality. `impact_type=potential` means a known dependency exists; it does not establish corrupted downstream data. Empty or unmapped graphs return `impact_status=UNKNOWN`, not a clean bill of health. Incident impact uses the incident's last-seen time and the pipeline's registered output asset.

An executor may `POST /api/v1/lineage/events` with a bounded OpenLineage-compatible `COMPLETE` RunEvent. The importer validates run/job/dataset identities and uses only explicit dataset-to-dataset entries from `job.facets.lineage`. It stores the event identity and canonical digest, but no raw event body or facet text. A repeated identical event returns the existing ID with zero new edges; the same identity with changed content returns 409. Producer URLs are recorded only, never fetched, and must be HTTPS without credentials or query strings. Client tenant IDs are rejected.

An event with only an input/output list registers datasets but creates no dependency edges. This prevents a two-input, two-output job from silently creating four false relationships. The importer currently supports only dataset entries in the [OpenLineage Lineage Job Facet](https://openlineage.io/docs/spec/facets/job-facets/lineage/) on a `COMPLETE` RunEvent. It does not ingest the full OpenLineage specification, dataset-level lineage facets, job-to-job links, field-level lineage, or live vendor connectors. Event edges are labeled `observed` as reported by submitted metadata; Takshyra has not independently verified the data flow.

## Evidence and limits

Seed edges have origin `declared` and source label `simulated`. The F04 quality incident points to the curated orders output, so its two downstream consumers are reported as potentially affected. The independent telemetry chain is not included. No financial impact, confirmed corruption, confidence probability or remediation decision is inferred from the graph.

Edges have `valid_from` and optional `valid_to`; traversal filters by the requested time. Existing incidents from before an output mapping or edge was recorded may show `UNKNOWN`. There is no edge-expiry management API yet. Asset reads are capped at 100 and do not paginate yet. The core remains a local development demo.

## Verify

Run `uv run --locked --extra test python -m pytest -q`, Ruff and `scripts/validate_blueprint.py`, then build Compose and run `scripts/smoke.py` through `scripts/smoke_m5.py` in order. Exact outcomes are in [implementation status](IMPLEMENTATION_STATUS.md).
