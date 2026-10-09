"""Exercise M2 through the Compose API and worker using local demo credentials."""

import base64
import json
import os
import time
import urllib.request
import uuid


def request(path: str, *, method: str = "GET", body: dict | None = None, key: str | None = None):
    token = base64.b64encode(f"demo-a-executor:{os.environ['DEMO_A_EXECUTOR_PASSWORD']}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "X-Tenant-Slug": "demo-a", "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(
        urllib.request.Request(f"http://localhost:8000{path}", data=data, headers=headers, method=method),
        timeout=5,
    ) as response:
        return json.load(response)


def run_fault(pipeline_id: str, fault: str):
    run = request(
        f"/api/v1/pipelines/{pipeline_id}/runs", method="POST",
        body={"demo_fault": fault}, key=f"m2-{fault}-{uuid.uuid4().hex}",
    )
    for _ in range(60):
        run = request(f"/api/v1/runs/{run['id']}")
        if run["execution_status"] in {"SUCCEEDED", "FAILED", "TIMED_OUT"}:
            return run
        time.sleep(1)
    raise AssertionError(f"M2 {fault} did not finish within 60 seconds")


pipeline = request("/api/v1/pipelines")["items"][0]
f02 = run_fault(pipeline["id"], "F02")
assert f02["execution_status"] == "SUCCEEDED"
assert [attempt["status"] for attempt in f02["attempts"]] == ["FAILED", "FAILED", "SUCCEEDED"]
f03 = run_fault(pipeline["id"], "F03")
assert f03["execution_status"] == "FAILED" and len(f03["attempts"]) == 3
f04 = run_fault(pipeline["id"], "F04")
assert (f04["execution_status"], f04["quality_status"], f04["publication_status"], f04["row_count"]) == ("SUCCEEDED", "FAIL", "QUARANTINED", 3)
incidents = request("/api/v1/incidents")["items"]
assert any(incident["run_id"] == f03["id"] and incident["category"] == "EXECUTION_FAILURE" for incident in incidents)
assert any(incident["run_id"] == f04["id"] and incident["category"] == "QUALITY_FAILURE" for incident in incidents)
freshness = request(f"/api/v1/demo/pipelines/{pipeline['id']}/freshness-miss", method="POST", body={})
assert freshness["run_id"] is None and freshness["category"] == "FRESHNESS_FAILURE"
assert freshness["provenance"] == "simulated"
print("M2 Compose smoke passed: F02 retry, F03 incident, F04 quality incident, F07 freshness incident")
