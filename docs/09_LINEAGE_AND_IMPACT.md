# Data lineage, blast-radius analysis and causality boundaries

## Registry
Assets include `Dataset`, `DataProduct`, `Dashboard`, `API`, `MLModel`, `FeatureTable`, optionally `Job`. Each asset has namespace+name, owner, criticality, tags, evidence source, last-seen time, sensitivity. Relationships are `PRODUCES`, `CONSUMES`, `DERIVES_FROM`, `SERVES`, each with origin (`observed`, `declared`, `inferred`), confidence class and validity window.

## OpenLineage compatibility
Use the standard's run/job/dataset identity and facets. Persist original event ID/producer/version, implement validation and idempotent ingest. Avoid treating all inputs to a job as sources of **all** outputs when fine-grained lineage is available; honor explicit edge/facet semantics. Extend using namespaced custom facets only if necessary. Never claim ingestion of every vendor's lineage without building specific parsers.

Official references:
- https://openlineage.io/docs/spec/facets/
- https://openlineage.io/docs/spec/facets/job-facets/lineage/
- https://openlineage.io/docs/spec/facets/dataset-facets/lineage/

## Blast radius algorithm (MVP)
Input: tenant, source asset(s), incident window, max_depth <= 8, node_limit <= 500. BFS/DFS over **authorized tenant edges** following affected direction. Record the path and edge provenance for each visited asset. Detect cycles, cap traversal, and return truncation warning. Downstream `potentially_affected` is not equivalent to confirmed invalid data. Add criticality/owner metadata for sorting, without inventing money-at-risk values.

## Useful API output
`affected_asset_id`, `asset_type`, `path_to_source`, `edge_origins`, `last_seen`, `criticality`, `owner`, `impact_type: confirmed | potential | unknown`, `reasons[]`.

## Temporal concerns
Lineage is versioned. Compare incident window to edge validity and dataset snapshots. If graph changes after a run, describe results as current-known dependency graph unless historical edges exist.

## Acceptance tests
Two independent outputs from one job must not falsely derive from all inputs; graph cycles terminate; hidden tenant assets never appear; stale/deleted edges handled; inferred paths labeled; empty graph returns no false assurance.
