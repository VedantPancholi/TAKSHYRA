"""Exercise contract version, held unknown and quarantined row drop in Compose."""

import base64
import json
import os
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid


def call(path, role="executor", method="GET", body=None, key=None):
    user = f"demo-b-{role}"
    password = os.environ[f"DEMO_B_{role.upper()}_PASSWORD"]
    headers = {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode(),
               "X-Tenant-Slug": "demo-b", "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    with urlopen(Request(f"http://localhost:8000{path}", headers=headers, data=data, method=method), timeout=5) as response:
        return json.load(response)


active = call("/api/v1/contracts")["items"][0]
definition = dict(active["definition"])
definition["expected_row_count"] = None
if active["definition"] != definition:
    route = f"/api/v1/contracts/{active['dataset_id']}/versions"
    try:
        active = call(route, "approver", "POST", definition)
    except HTTPError as exc:
        if exc.code != 409:
            raise
        active = call("/api/v1/contracts")["items"][0]
assert active["definition"]["expected_row_count"] is None
pipeline = call("/api/v1/pipelines")["items"][0]["id"]


def run(body):
    created = call(f"/api/v1/pipelines/{pipeline}/runs", method="POST", body=body,
                   key=f"m4-{uuid.uuid4().hex}")
    for _ in range(60):
        current = call(f"/api/v1/runs/{created['id']}")
        if current["execution_status"] in {"SUCCEEDED", "FAILED", "TIMED_OUT"}:
            return current
        time.sleep(1)
    raise AssertionError("M4 run timed out")


clean = run({})
assert (clean["execution_status"], clean["quality_status"], clean["publication_status"]) == (
    "SUCCEEDED", "UNKNOWN", "HELD"), clean
assert clean["contract_version"] == active["version"]
manifest = call(f"/api/v1/runs/{clean['id']}/manifest")
assert manifest["manifest"]["contract_hash"] == active["definition_hash"]

row_drop = run({"demo_fault": "F04"})
assert (row_drop["execution_status"], row_drop["quality_status"], row_drop["publication_status"]) == (
    "SUCCEEDED", "FAIL", "QUARANTINED"), row_drop
print("M4 Compose smoke passed: bound version, unknown hold, row-drop quarantine")
