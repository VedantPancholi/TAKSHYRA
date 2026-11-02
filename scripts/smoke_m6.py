"""Exercise the M6 web proxy and an incident-to-action handoff in Compose."""

import base64
import json
import os
import urllib.request
from urllib.error import HTTPError
import uuid

ROOT = "http://web:3000"


def request(path, user=None, password=None, method="GET", body=None, tenant="demo-a", key=None):
    headers = {}
    if user is not None:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        headers.update({"Authorization": f"Basic {token}", "X-Tenant-Slug": tenant})
    if body is not None:
        headers["Content-Type"] = "application/json"
    if key is not None:
        headers["Idempotency-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(
        urllib.request.Request(f"{ROOT}{path}", data=data, headers=headers, method=method), timeout=12,
    ) as response:
        return json.load(response) if path.startswith("/api/") else response.read()


def actor(role, path, method="GET", body=None, key=None):
    return request(path, f"demo-a-{role}", os.environ[f"DEMO_A_{role.upper()}_PASSWORD"], method, body, key=key)


with urllib.request.urlopen(ROOT, timeout=12) as response:
    assert response.status == 200 and b"TAKSHYRA" in response.read()

try:
    request("/api/core/me")
    raise AssertionError("Anonymous proxy access succeeded")
except HTTPError as exc:
    assert exc.code == 401

try:
    actor("executor", "/api/core/lineage/events", "POST", {})
    raise AssertionError("Unlisted proxy route succeeded")
except HTTPError as exc:
    assert exc.code == 404

assert actor("viewer", "/api/core/me")["role"] == "viewer"
pipeline_id = actor("executor", "/api/core/pipelines")["items"][0]["id"]
incident = actor("executor", f"/api/core/demo/pipelines/{pipeline_id}/freshness-miss", "POST", {})
incident_id = incident["id"]
assert actor("viewer", f"/api/core/incidents/{incident_id}")["id"] == incident_id
assert "items" in actor("viewer", f"/api/core/incidents/{incident_id}/impact")

try:
    actor("viewer", "/api/core/action-proposals", "POST", {
        "action_type": "incident.annotate", "target_id": incident_id, "parameters": {"note": "Denied"},
    }, uuid.uuid4().hex)
    raise AssertionError("Viewer created a proposal")
except HTTPError as exc:
    assert exc.code == 403

annotation = actor("executor", "/api/core/action-proposals", "POST", {
    "action_type": "incident.annotate", "target_id": incident_id, "parameters": {"note": "M6 web smoke"},
}, uuid.uuid4().hex)
assert annotation["policy_decision"] == "ALLOW"
verified = actor("executor", f"/api/core/action-proposals/{annotation['id']}/execute", "POST", {})
assert verified["verification_status"] == "VERIFIED"

pause = actor("executor", "/api/core/action-proposals", "POST", {
    "action_type": "pipeline.pause_demo", "target_id": pipeline_id, "parameters": {},
}, uuid.uuid4().hex)
assert pause["status"] == "AWAITING_APPROVAL"
approved = actor("approver", f"/api/core/action-proposals/{pause['id']}/approve", "POST", {})
assert approved["status"] == "APPROVED"
done = actor("executor", f"/api/core/action-proposals/{pause['id']}/execute", "POST", {})
assert done["verification_status"] == "VERIFIED"
print("M6 web smoke passed: page, proxy allowlist, viewer denial, incident, annotation, approval and verification")
