# M4 versioned orders contracts and publication gate

M4 applies to the fixed synthetic `demo.orders_curated` dataset in each demo tenant. Migration `0005_contracts` creates tenant-scoped datasets and contract versions and adds a contract version reference to runs. Seed creates version 1 for each tenant. A run binds the active version when queued; later versions do not change its evaluation. Existing pre-M4 runs have no bound version and use the seed contract if processed after migration. An old-format manifest on an unfinished pre-M4 run fails closed during recovery.

## API

All routes require development Basic credentials and `X-Tenant-Slug`. A tenant member can call `GET /api/v1/contracts` and `GET /api/v1/contracts/{dataset_id}/versions/{version}`. An approver or admin can call `POST /api/v1/contracts/{dataset_id}/versions` with a complete `OrdersContract` JSON body. The server assigns the next version, stores canonical JSON and its SHA-256 hash, sets it active, and writes an audit event. Repeating the active definition returns 409. Unknown fields, client tenant IDs and unsupported rule types return 422. There is no update/delete endpoint for stored versions.

`GET /api/v1/runs/{id}` includes the bound contract version/hash and check outcomes. `GET /api/v1/runs/{id}/manifest` returns checksum, row count, schema field names, contract version/hash and rule evidence only after a successful transform. It checks tenant membership and the current DB publication state. It does not return Parquet rows or a download path. Cross-tenant run/manifest and contract reads return 404.

## Gate

The fixed CSV runner writes Parquet and a checksum manifest under a server-generated run path. It checks required schema fields, unexpected fields under `allow_extra_fields`, timestamp/decimal values, expected row ratio, customer null rate, duplicate order IDs, optional freshness, and source/output row equality. Missing count baseline yields `UNKNOWN`; no source rows yield `UNKNOWN` for rate checks. A failed check makes execution `SUCCEEDED`, quality `FAIL`, publication `QUARANTINED`. Unknown checks without failures make publication `HELD`. Only all-pass results become `PUBLISHED`. `runs.publication_status` in PostgreSQL is the visibility authority; a manifest on disk alone is never published.

The baseline of four rows is specific to the packaged synthetic fixture. `F04` drops one of four rows and produces a failed row ratio and source/output match. These values are simulated demo data. Freshness is evaluated only for a contract version with `max_age_hours`; the seed version has no freshness rule because the fixed fixture dates age over time.

## Limitations and recovery

The database and filesystem do not share an atomic transaction. A crash after writing the manifest but before committing the run leaves an inaccessible staged artifact; lease recovery reuses a checksum-valid manifest if the contract hash/version match. A contract mismatch fails the run closed. Garbage collection and an external consumer publish pointer are not implemented. This gate controls only the Takshyra run state and its manifest API, not external downstream storage.

## Verify

Run `uv run --locked --extra test python -m pytest -q`, Ruff, blueprint validation, then `docker compose up --build -d --wait`, `docker compose exec -T api alembic current`, and the M1–M4 smoke scripts. Migration and smoke outcomes are recorded in [implementation status](IMPLEMENTATION_STATUS.md).
