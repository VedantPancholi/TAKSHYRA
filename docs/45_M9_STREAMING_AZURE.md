# M9 first slice: local stream lab and Azure Data Factory observer

## Local demo

Sign in to the operations console as a demo executor and use **Telemetry checks**. Choose a scenario and run it. The seeded `telemetry_stream_demo_v1` pipeline processes four fixed synthetic events in memory; no broker or cloud service is involved. `GET /api/v1/stream-observations` returns up to 50 recent observations in the authenticated tenant. `POST /api/v1/stream-observations/demo` accepts only one of `CLEAN`, `SCHEMA_V15`, `SINK_GAP`, `CONSUMER_LAG`, `DUPLICATE`, or `LATE_EVENT`. It is development-only and executor-only. Failed scenarios create a tenant-scoped incident with an evidence event referencing the observation. The telemetry output asset is linked to the seeded operations dashboard for potential-impact display.

The lab reports source, unique, decoded, written, dead-letter, duplicate and late counts, maximum synthetic event-to-ingest lag, and source-to-sink gap. `SCHEMA_V15` and `SINK_GAP` demonstrate different causes of missing sink events. Duplicate delivery is deduplicated and passes. No offsets, consumer group, checkpoint, Parquet sink, or real broker exists in this slice. Counts are evidence about the synthetic fixture only.

Run the end-to-end check after `docker compose up --build -d --wait`:

```powershell
docker compose exec -T api python scripts/smoke_m9.py
```

## ADF observation contract

`takshyra.adf.AdfObserver` calls only the ADF `queryPipelineRuns` read query for an exact allowlisted subscription, resource group and factory. The Azure API uses HTTP POST for this query; the adapter has no trigger, cancel, edit or delete operation. It requires a timezone-aware window of at most 24 hours, caps output at 100 runs and three pages, rejects repeated cursors, and returns a truncation flag. It retains only run ID, pipeline name, status and start/end timestamps; raw messages, parameters and activity outputs are discarded. The default tests inject a mock transport and make no Azure call.

An optional live probe is in `scripts/adf_observe.py`. It is **off by default**, requires `ENABLE_LIVE_AZURE_TESTS=true`, an installed `azure-identity` package, a credential available to `DefaultAzureCredential`, and these explicit environment values: `TAKSHYRA_TENANT_SLUG`, `AZURE_ADF_SUBSCRIPTION_ID`, `AZURE_ADF_RESOURCE_GROUP`, and `AZURE_ADF_FACTORY_NAME`. Run only against an approved sandbox factory with read access. The script queries the last hour, at most 25 runs, prints normalized metadata, and never persists a token. This branch has not run a live Azure probe.

The endpoint and API version follow [Microsoft's ADF pipeline-run query reference](https://learn.microsoft.com/en-us/rest/api/datafactory/pipeline-runs/query-by-factory?view=rest-datafactory-2018-06-01). The optional credential approach follows [Azure Identity's DefaultAzureCredential documentation](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential?view=azure-python). Confirm permissions for the actual sandbox before enabling live access.

## Remaining M9 work

At the first-slice merge, a real local broker/consumer with checkpoint, retention and replay tests, plus Azure Event Hubs and Monitor adapters, remained. ADF runs were observed through a separate probe and were not yet persisted as core incidents. No Azure or AWS pipeline is modified, and there is no new-pipeline builder.

## Follow-up: ADF run ingestion branch

`feat/m9-adf-ingestion` adds a local binding from one tenant, ADF factory and external pipeline name to a Takshyra pipeline. `scripts/adf_ingest.py` performs an opted-in, read-only ADF query and stores only the observer's normalized run ID, pipeline name, status and timestamps. The script requires `ENABLE_LIVE_AZURE_TESTS=true`, `azure-identity`, a configured `DATABASE_URL`, the four existing ADF scope variables, `TAKSHYRA_ADF_LOCAL_PIPELINE` and `AZURE_ADF_PIPELINE_NAME`. The process must have network access to both Azure management and the Takshyra database; the standard local image does not install the optional Azure Identity package. No live Azure ingestion has been tested.

The importer rejects truncated query results and binds each local pipeline to one exact ADF target. Repeated polls update the same run observation. A first observed `Failed` or `Cancelled` state records an incident and evidence reference; later polls do not duplicate it. A terminal status changing to another terminal state is rejected for review. It never marks a local recovery as verified or changes an Azure pipeline. `GET /api/v1/adf-observations` lists the latest 50 observations within the signed-in tenant. The incident center shows any failure incident through its existing API.

The mocked database and web-proxy check runs after Compose is healthy:

```powershell
docker compose exec -T api python scripts/smoke_m9_adf.py
```

This smoke uses `simulated` provenance and never contacts Azure. The broker and other Azure adapters described above still remain.

## Failure-case checks

The follow-up test branch adds malformed-provider and transaction tests. A batch is atomic even if the caller catches an error and commits its outer transaction. The importer verifies a stored binding and locks it while ingesting on PostgreSQL, so overlapping polls for the same ADF pipeline are serialized. Run the mocked PostgreSQL fault check after Compose is healthy:

```powershell
docker compose exec -T api python scripts/smoke_m9_adf_faults.py
```

This check exercises a late malformed run, repeat polling and two overlapping polls. It does not connect to Azure.
See the [failure-case matrix](46_M9_ADF_FAILURE_TESTING.md) for the tested boundaries and remaining limits.
