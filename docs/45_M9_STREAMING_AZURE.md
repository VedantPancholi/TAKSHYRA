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

This is the first slice of M9. A real local broker/consumer with checkpoint, retention and replay tests, plus Azure Event Hubs and Monitor adapters, remains. ADF runs are observed through a separate probe and are not yet persisted as core incidents. No Azure or AWS pipeline is modified, and there is no new-pipeline builder.
