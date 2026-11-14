"""Exercise M9 local telemetry via the web proxy and API."""

import base64
import json
import os
import urllib.request

BASE = "http://web:3000/api/core"


def call(role, path, method="GET", body=None):
    username = f"demo-a-{role}"
    password = os.environ[f"DEMO_A_{role.upper()}_PASSWORD"]
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "X-Tenant-Slug": "demo-a"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{BASE}/{path}", data=json.dumps(body).encode() if body is not None else None,
        headers=headers, method=method,
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


failed = call("executor", "stream-observations/demo", "POST", {"scenario": "SINK_GAP"})
assert failed["status"] == "FAIL" and failed["metrics"]["source_sink_gap"] == 1
assert failed["incident_id"]
detail = call("viewer", f"incidents/{failed['incident_id']}")
assert detail["error_code"] == "STREAM_RECONCILIATION_GAP"
assert any(event["source_kind"] == "STREAM_OBSERVATION" for event in detail["timeline"])
assert call("viewer", "stream-observations")["items"][0]["id"] == failed["id"]
clean = call("executor", "stream-observations/demo", "POST", {"scenario": "DUPLICATE"})
assert clean["status"] == "PASS" and clean["metrics"]["duplicates"] == 1
assert clean["metrics"]["written"] == 4 and clean["incident_id"] is None
print("M9 Compose smoke passed: stream mismatch incident and safe duplicate delivery")
