"""Exercise policy, approval, action effect and verification in Compose."""

import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
import urllib.request
from urllib.error import HTTPError
import uuid


def request(path: str, user: str, password: str, method: str = "GET", body: dict | None = None, key: str | None = None):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "X-Tenant-Slug": "demo-a", "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(
        urllib.request.Request(f"http://localhost:8000{path}", data=data, headers=headers, method=method), timeout=5,
    ) as response:
        return json.load(response)


def executor(path: str, method: str = "GET", body: dict | None = None, key: str | None = None):
    return request(path, "demo-a-executor", os.environ["DEMO_A_EXECUTOR_PASSWORD"], method, body, key)


def approver(path: str, method: str = "GET"):
    return request(path, "demo-a-approver", os.environ["DEMO_A_APPROVER_PASSWORD"], method)


pipeline_id = executor("/api/v1/pipelines")["items"][0]["id"]
incident_id = executor(f"/api/v1/demo/pipelines/{pipeline_id}/freshness-miss", "POST", {})["id"]
prefix = "/api/v1/action-proposals"
annotation = executor(prefix, "POST", {"action_type": "incident.annotate", "target_id": incident_id,
                                       "parameters": {"note": "Checked by local smoke"}}, f"m3-note-{uuid.uuid4().hex}")
assert annotation["policy_decision"] == "ALLOW"


def execute_annotation():
    try:
        return executor(f"{prefix}/{annotation['id']}/execute", "POST")["status"]
    except HTTPError as exc:
        return f"HTTP_{exc.code}"


with ThreadPoolExecutor(max_workers=2) as pool:
    outcomes = list(pool.map(lambda _: execute_annotation(), range(2)))
assert "VERIFIED" in outcomes and set(outcomes) <= {"VERIFIED", "HTTP_409"}, outcomes
timeline = executor(f"/api/v1/incidents/{incident_id}")["timeline"]
assert sum(item["kind"] == "ANNOTATED" and item["source_id"] == annotation["id"] for item in timeline) == 1

pause = executor(prefix, "POST", {"action_type": "pipeline.pause_demo", "target_id": pipeline_id,
                                  "parameters": {}}, f"m3-pause-{uuid.uuid4().hex}")
assert pause["policy_decision"] == "REQUIRES_APPROVAL" and pause["status"] == "AWAITING_APPROVAL"
approved = approver(f"{prefix}/{pause['id']}/approve", "POST")
assert approved["status"] == "APPROVED"
done = executor(f"{prefix}/{pause['id']}/execute", "POST")
assert done["verification_status"] == "VERIFIED" and done["status"] == "VERIFIED"

denied = executor(prefix, "POST", {"action_type": "shell.execute", "target_id": incident_id,
                                   "parameters": {}}, f"m3-deny-{uuid.uuid4().hex}")
assert denied["policy_decision"] == "DENY" and denied["status"] == "DENIED"
print("M3 Compose smoke passed: ALLOW, REQUIRES_APPROVAL, DENY, effect verification")
