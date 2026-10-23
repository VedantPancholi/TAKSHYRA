"""Check seeded downstream impact and explicit event mapping through Compose."""

import base64
from datetime import datetime, timezone
import json
import os
import time
from urllib.request import Request, urlopen
import uuid


def call(path, method="GET", body=None, key=None):
    user = "demo-a-executor"
    password = os.environ["DEMO_A_EXECUTOR_PASSWORD"]
    headers = {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode(),
               "X-Tenant-Slug": "demo-a", "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    with urlopen(Request(f"http://localhost:8000{path}", headers=headers, data=data, method=method), timeout=5) as response:
        return json.load(response)


assets = call("/api/v1/assets")["items"]
curated = next(asset for asset in assets if asset["name"] == "demo.orders_curated")
graph = call(f"/api/v1/lineage/{curated['id']}/impact")
assert {item["name"] for item in graph["items"]} == {"demo.revenue_dashboard", "demo.sales_forecast"}
assert all(item["impact_type"] == "potential" for item in graph["items"])

pipeline = call("/api/v1/pipelines")["items"][0]["id"]
run = call(f"/api/v1/pipelines/{pipeline}/runs", "POST", {"demo_fault": "F04"}, f"m5-{uuid.uuid4().hex}")
for _ in range(60):
    current = call(f"/api/v1/runs/{run['id']}")
    if current["execution_status"] in {"SUCCEEDED", "FAILED", "TIMED_OUT"}:
        break
    time.sleep(1)
else:
    raise AssertionError("M5 incident run timed out")
assert (current["execution_status"], current["quality_status"], current["publication_status"]) == (
    "SUCCEEDED", "FAIL", "QUARANTINED")
incident = next(item for item in call("/api/v1/incidents")["items"] if item["run_id"] == run["id"])
impact = call(f"/api/v1/incidents/{incident['id']}/impact")
assert {item["name"] for item in impact["items"]} == {"demo.revenue_dashboard", "demo.sales_forecast"}

source_a = {"namespace": "m5.smoke", "name": f"source.a.{uuid.uuid4().hex}"}
source_b = {"namespace": "m5.smoke", "name": f"source.b.{uuid.uuid4().hex}"}
target_a = {"namespace": "m5.smoke", "name": f"target.a.{uuid.uuid4().hex}"}
target_b = {"namespace": "m5.smoke", "name": f"target.b.{uuid.uuid4().hex}"}
event = {"eventType": "COMPLETE", "eventTime": datetime.now(timezone.utc).isoformat(),
         "producer": "https://example.invalid/m5-smoke", "run": {"runId": str(uuid.uuid4())},
         "job": {"namespace": "m5.smoke", "name": "split", "facets": {"lineage": {"entries": [
             {**target_a, "type": "DATASET", "inputs": [{**source_a, "type": "DATASET"}]},
             {**target_b, "type": "DATASET", "inputs": [{**source_b, "type": "DATASET"}]},
         ]}}}, "inputs": [source_a, source_b], "outputs": [target_a, target_b]}
accepted = call("/api/v1/lineage/events", "POST", event)
assert accepted["edge_count"] == 2
again = call("/api/v1/lineage/events", "POST", event)
assert again["id"] == accepted["id"] and again["edge_count"] == 0
source = next(asset for asset in call("/api/v1/assets")["items"] if asset["name"] == source_a["name"])
mapped = call(f"/api/v1/lineage/{source['id']}/impact")
assert [item["name"] for item in mapped["items"]] == [target_a["name"]]
print("M5 Compose smoke passed: seeded impact, incident link, exact event mapping, idempotency")
