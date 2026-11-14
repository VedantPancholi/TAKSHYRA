"""Exercise mocked ADF polling through PostgreSQL and the web proxy."""

import base64
import json
import os
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.adf import AdfObserver, AdfScope
from takshyra.adf_ingestion import ingest_runs, register_binding
from takshyra.db import engine
from takshyra.models import Tenant

run_id = str(uuid.uuid4())
with Session(engine()) as db:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == "demo-a"))
    scope = AdfScope(tenant.id, "00000000-0000-0000-0000-000000000001", "rg-smoke", "factory-smoke")
    observer = AdfObserver(
        tenant_id=tenant.id, allowed_targets=frozenset({scope.target}),
        transport=lambda _url, _body: {"value": [{
            "runId": run_id, "pipelineName": "orders-adf-smoke", "status": "Failed",
            "parameters": {"secret": "never-store-this"},
        }]},
    )
    until = datetime.now(timezone.utc)
    result = observer.query(scope, until - timedelta(minutes=5), until)
    binding = register_binding(
        db, scope=scope, local_name="orders_adf_smoke", external_name="orders-adf-smoke",
    )
    counts = ingest_runs(db, scope=scope, binding=binding, result=result, provenance="simulated")
    db.commit()
assert counts["created"] == counts["incidents"] == 1

username = "demo-a-viewer"
password = os.environ["DEMO_A_VIEWER_PASSWORD"]
token = base64.b64encode(f"{username}:{password}".encode()).decode()
request = urllib.request.Request(
    "http://web:3000/api/core/adf-observations",
    headers={"Authorization": f"Basic {token}", "X-Tenant-Slug": "demo-a"},
)
with urllib.request.urlopen(request, timeout=12) as response:
    payload = json.load(response)
row = next(item for item in payload["items"] if item["external_run_id"] == run_id)
assert row["provenance"] == "simulated" and row["status"] == "Failed"
assert "never-store-this" not in json.dumps(payload)
request = urllib.request.Request(
    "http://web:3000/api/core/incidents",
    headers={"Authorization": f"Basic {token}", "X-Tenant-Slug": "demo-a"},
)
with urllib.request.urlopen(request, timeout=12) as response:
    incidents = json.load(response)
assert any(item["error_code"] == "ADF_RUN_FAILED" for item in incidents["items"])
print("M9 ADF Compose smoke passed: normalized run, tenant API and failure incident")
