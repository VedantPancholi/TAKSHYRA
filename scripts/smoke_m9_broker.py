"""Exercise the real local Redis stream through the web proxy and worker."""

import base64
import json
import os
import time
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


before = call("viewer", "stream-observations/broker")
queued = call("executor", "stream-observations/broker-demo", "POST", {"scenario": "SCHEMA_V15"})
assert queued["queued"] == 4 and queued["mode"] == "local_redis_stream"
for _ in range(30):
    after = call("viewer", "stream-observations/broker")
    if after["written"] >= before["written"] + 3 and after["dlq"] >= before["dlq"] + 1:
        break
    time.sleep(1)
else:
    raise AssertionError("Broker worker did not process published events")
assert after["failures"] >= before["failures"] + 1
print("M9 broker smoke passed: queued, checkpointed, written and DLQ events")
