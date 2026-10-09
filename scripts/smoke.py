"""Run inside the API container after Compose is healthy."""

import base64
import json
import os
import time
import urllib.request
import uuid
from pathlib import Path

import pyarrow.parquet as pq


def request(path: str, method: str = "GET", body: dict | None = None):
    token = base64.b64encode(f"demo-a-executor:{os.environ['DEMO_A_EXECUTOR_PASSWORD']}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "X-Tenant-Slug": "demo-a", "Idempotency-Key": f"smoke-{KEY}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(f"http://localhost:8000{path}", data=data, headers=headers, method=method), timeout=5) as response:
        return json.load(response)


KEY = uuid.uuid4().hex
pipeline = request("/api/v1/pipelines")["items"][0]
run = request(f"/api/v1/pipelines/{pipeline['id']}/runs", "POST", {})
for _ in range(30):
    run = request(f"/api/v1/runs/{run['id']}")
    if run["execution_status"] in {"SUCCEEDED", "FAILED", "TIMED_OUT"}:
        break
    time.sleep(1)
assert run["execution_status"] == "SUCCEEDED", run
assert run["quality_status"] == "PASS" and run["publication_status"] == "PUBLISHED", run
manifest = Path(run["manifest_path"])
assert manifest.is_file()
assert pq.read_metadata(manifest.with_name("orders.parquet")).num_rows == run["row_count"] == 4
print(f"M1 Compose smoke passed: run {run['id']}, 4 Parquet rows")
