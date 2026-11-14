# M9 ADF failure-case verification

**Scope:** The read-only ADF observer and local ingestion path after PR #14. Provider responses are mocked; PostgreSQL runs in Docker Compose. No Azure credentials or live factory were used.

| Failure case | Expected result | Verified by |
| --- | --- | --- |
| A failed run is followed by a malformed run | Neither run nor its incident is committed, even if the caller commits after catching the error | SQLite test and PostgreSQL fault smoke |
| The same run appears twice in one response | Entire batch is rejected without partial evidence | SQLite test |
| A repeated poll sees the same failed run | Existing observation updates; no new incident evidence | SQLite test and PostgreSQL fault smoke |
| Two distinct failed runs arrive together | Two evidence events; incident occurrence count increases twice | SQLite test |
| Two polls overlap before the first commits | Second waits for the binding lock, then updates the existing run | PostgreSQL fault smoke with two sessions |
| A forged or mismatched binding is supplied | No observation is ingested | SQLite test |
| Provider fields are malformed or contain secrets | Invalid IDs, names and status types are rejected; raw parameters/messages never enter the stored observation | Mock observer tests and API test |
| Timestamp is naive, invalid, too long or reversed | Batch is rejected without partial evidence | SQLite test |
| Query is cross-tenant, too wide, unbounded or truncated | Observation is refused before an unsafe ingest | Mock observer and ingestion tests |
| Live ingestion is attempted without opt-in | Script exits before contacting Azure or the database | Compose command |

## Commands and results

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_m9.py tests\test_m9_adf_ingestion.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check takshyra tests migrations scripts
docker compose up --build -d --wait
docker compose exec -T api python scripts/smoke_m9_adf.py
docker compose exec -T api python scripts/smoke_m9_adf_faults.py
```

Results: 20 focused tests passed; 50 full-suite tests passed; Ruff passed; all Compose services were healthy; normal and fault smokes passed. The existing Starlette/AnyIO deprecation warning remains. The disabled live-ingestion command exited with the expected opt-in message.

## Limits

The overlapping-poll check uses two PostgreSQL sessions and one shared run. It does not measure sustained load, provider throttling, network partitions, Azure role permissions or real ADF response drift. A live sandbox probe remains necessary before claiming Azure integration is verified.
