"""Exercise M8 replay, approval, reprocessing and recovery through Compose."""

import base64
import json
import os
import time
import urllib.request
import uuid

PROXY = "http://web:3000/api/core"
CORE = "http://localhost:8000/api/v1"


def call(role, path, method="GET", body=None, key=None, *, direct=False):
    username = f"demo-a-{role}"
    password = os.environ[f"DEMO_A_{role.upper()}_PASSWORD"]
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "X-Tenant-Slug": "demo-a"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if key:
        headers["Idempotency-Key"] = key
    request = urllib.request.Request(
        f"{CORE if direct else PROXY}/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def wait_for(check, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result is not None:
            return result
        time.sleep(1)
    raise AssertionError("Timed out waiting for the worker")


pipeline = next(item for item in call("executor", "pipelines")["items"]
                if item["source_kind"] == "seed_orders_v1")
source = call("executor", f"pipelines/{pipeline['id']}/runs", "POST",
              {"demo_fault": "F04"}, str(uuid.uuid4()))
source_id = source["id"]


def source_incident():
    run = call("executor", f"runs/{source_id}", direct=True)
    if run["execution_status"] != "SUCCEEDED":
        return None
    assert run["quality_status"] == "FAIL" and run["publication_status"] == "QUARANTINED"
    return next((item for item in call("executor", "incidents")["items"]
                 if item["run_id"] == source_id), None)


incident = wait_for(source_incident)
replay = call("executor", f"incidents/{incident['id']}/shadow-replays", "POST", {})
assert replay["status"] == "SUPPORTED"
assert (replay["baseline_row_count"], replay["replay_row_count"]) == (3, 4)
proposal = call("executor", "action-proposals", "POST", {
    "action_type": "pipeline.reprocess_demo", "target_id": source_id,
    "parameters": {"shadow_report_id": replay["id"]},
}, str(uuid.uuid4()))
assert proposal["status"] == "AWAITING_APPROVAL"
approved = call("approver", f"action-proposals/{proposal['id']}/approve", "POST", {})
assert approved["status"] == "APPROVED"
executed = call("executor", f"action-proposals/{proposal['id']}/execute", "POST", {})
assert executed["status"] == "VERIFIED"
recovery_run_id = executed["effect_ref_id"]


def finished_recovery():
    run = call("executor", f"runs/{recovery_run_id}", direct=True)
    return run if run["execution_status"] in {"SUCCEEDED", "FAILED"} else None


recovered = wait_for(finished_recovery)
assert (recovered["execution_status"], recovered["quality_status"],
        recovered["publication_status"], recovered["row_count"]) == (
            "SUCCEEDED", "PASS", "PUBLISHED", 4,
        )
outcome = call("executor", f"action-proposals/{proposal['id']}/verify-recovery", "POST", {})
assert outcome["status"] == "VERIFIED", outcome
assert call("executor", f"incidents/{incident['id']}")["status"] == "RESOLVED"
print("M8 Compose smoke passed: replay, approval, reprocess and verified recovery")
