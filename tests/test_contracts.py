from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.api import app
from takshyra.config import Settings
from takshyra.contracts import OrdersContract, SEED_CONTRACT, decision, evaluate
from takshyra.models import ContractVersion, Run, now
from takshyra.runner import transform
from takshyra.worker import claim, process_one
from test_foundation import auth, local as m4_setup, pipeline_id  # noqa: F401


def test_version_binding_unknown_gate_and_tenant_access(request):
    settings, engine = request.getfixturevalue("m4_setup")
    client = TestClient(app)
    headers, credentials = auth()
    approver_headers, approver_credentials = auth("demo-a-approver")
    viewer_headers, viewer_credentials = auth("demo-a-viewer")
    other_headers, other_credentials = auth("demo-b-executor", "demo-b")
    listed = client.get("/api/v1/contracts", headers=viewer_headers, auth=viewer_credentials)
    assert listed.status_code == 200
    initial = listed.json()["items"][0]
    assert initial["version"] == 1
    pid = pipeline_id(client)
    old_run = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={}).json()
    assert old_run["contract_version"] == 1
    definition = {**initial["definition"], "expected_row_count": None}
    route = f"/api/v1/contracts/{initial['dataset_id']}/versions"
    assert client.post(route, headers=viewer_headers, auth=viewer_credentials, json=definition).status_code == 403
    assert client.post(route, headers=headers, auth=credentials, json=definition).status_code == 403
    assert client.post(route, headers=other_headers, auth=other_credentials, json=definition).status_code == 403
    assert client.get(f"{route}/1", headers=other_headers, auth=other_credentials).status_code == 404
    assert client.post(route, headers=approver_headers, auth=approver_credentials,
                       json={**definition, "tenant_id": "demo-b"}).status_code == 422
    weakened = {**definition, "schema_fields": [
        {**field, "required": False} if field["name"] == "order_id" else field
        for field in definition["schema_fields"]]}
    assert client.post(route, headers=approver_headers, auth=approver_credentials, json=weakened).status_code == 422
    created = client.post(route, headers=approver_headers, auth=approver_credentials, json=definition)
    assert created.status_code == 201 and created.json()["version"] == 2
    assert client.post(route, headers=approver_headers, auth=approver_credentials, json=definition).status_code == 409
    headers["Idempotency-Key"] = "m4-version-two"
    new_run = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={}).json()
    assert new_run["contract_version"] == 2
    assert process_one(settings, "m4-old-worker")
    assert process_one(settings, "m4-new-worker")
    old_result = client.get(f"/api/v1/runs/{old_run['id']}", headers=headers, auth=credentials).json()
    new_result = client.get(f"/api/v1/runs/{new_run['id']}", headers=headers, auth=credentials).json()
    assert (old_result["quality_status"], old_result["publication_status"]) == ("PASS", "PUBLISHED")
    assert (new_result["quality_status"], new_result["publication_status"]) == ("UNKNOWN", "HELD")
    assert {item["rule_version"] for item in new_result["quality_results"]} == {2}
    manifest = client.get(f"/api/v1/runs/{new_run['id']}/manifest", headers=viewer_headers, auth=viewer_credentials)
    assert manifest.status_code == 200
    assert manifest.json()["manifest"]["contract_hash"] == created.json()["definition_hash"]
    assert client.get(f"/api/v1/runs/{new_run['id']}/manifest", headers=other_headers, auth=other_credentials).status_code == 404
    with Session(engine) as db:
        assert db.scalar(select(ContractVersion).where(ContractVersion.version == 1,
            ContractVersion.tenant_id == db.get(Run, old_run["id"]).tenant_id)).definition_hash == initial["definition_hash"]


def test_schema_gate_and_quarantine_manifest(request, tmp_path):
    settings, _ = request.getfixturevalue("m4_setup")
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    missing = tmp_path / "missing.csv"
    missing.write_text("order_id,order_ts,amount\n1,2026-01-01T00:00:00Z,1\n", encoding="utf-8")
    run = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={}).json()
    changed = Settings(settings.app_env, settings.database_url, settings.redis_url, settings.output_dir,
                       str(missing), settings.demo_passwords)
    assert process_one(changed, "m4-missing-field")
    result = client.get(f"/api/v1/runs/{run['id']}", headers=headers, auth=credentials).json()
    assert (result["execution_status"], result["quality_status"], result["publication_status"]) == (
        "SUCCEEDED", "FAIL", "QUARANTINED")
    assert next(item for item in result["quality_results"] if item["rule_id"] == "schema")["outcome"] == "FAIL"
    manifest_route = f"/api/v1/runs/{run['id']}/manifest"
    assert client.get(manifest_route, headers=headers, auth=credentials).json()["publication_status"] == "QUARANTINED"
    manifest_path = Path(result["manifest_path"])
    altered = json.loads(manifest_path.read_text(encoding="utf-8"))
    altered["quality_status"] = "PASS"
    manifest_path.write_text(json.dumps(altered), encoding="utf-8")
    assert client.get(manifest_route, headers=headers, auth=credentials).status_code == 503


def test_recovery_rejects_changed_manifest(request):
    settings, engine = request.getfixturevalue("m4_setup")
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    run_id = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={}).json()["id"]
    with Session(engine) as db:
        assert claim(db, "m4-crashed")
        run = db.get(Run, run_id)
        transform(settings.fixture_path, settings.output_dir, run.tenant_id, run_id)
        run.lease_until = now() - timedelta(seconds=1)
        db.commit()
        path = Path(settings.output_dir) / run.tenant_id / run_id / "manifest.json"
    altered = json.loads(path.read_text(encoding="utf-8"))
    altered["quality_status"] = "FAIL"
    path.write_text(json.dumps(altered), encoding="utf-8")
    assert process_one(settings, "m4-replacement")
    result = client.get(f"/api/v1/runs/{run_id}", headers=headers, auth=credentials).json()
    assert (result["execution_status"], result["publication_status"], result["error_code"]) == (
        "FAILED", "HELD", "CONTRACT_MANIFEST_MISMATCH")


def test_contract_rule_edges():
    rows = [{"order_id": "1", "order_ts": "2026-10-23T09:00:00Z", "amount": "1", "customer_id": "c"},
            {"order_id": "1", "order_ts": "2026-10-23T09:00:00Z", "amount": "2", "customer_id": "c"}]
    fields = list(rows[0])
    checks = evaluate(SEED_CONTRACT, rows, fields)
    assert next(item for item in checks if item["rule_id"] == "order_id_duplicate_rate")["outcome"] == "FAIL"
    optional = OrdersContract.model_validate({**SEED_CONTRACT.model_dump(), "allow_extra_fields": True,
        "expected_row_count": None, "max_age_hours": 2})
    checks = evaluate(optional, rows, fields + ["optional_note"], datetime(2026, 10, 23, 10, tzinfo=timezone.utc))
    assert next(item for item in checks if item["rule_id"] == "schema")["outcome"] == "PASS"
    strict = evaluate(SEED_CONTRACT, rows, fields + ["optional_note"])
    assert next(item for item in strict if item["rule_id"] == "schema")["outcome"] == "FAIL"
    assert next(item for item in checks if item["rule_id"] == "row_count_ratio")["outcome"] == "UNKNOWN"
    assert next(item for item in checks if item["rule_id"] == "freshness")["outcome"] == "PASS"
    assert decision(evaluate(SEED_CONTRACT, [], fields)) == ("FAIL", "QUARANTINED")
