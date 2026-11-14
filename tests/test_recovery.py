"""M8 replay and recovery checks across the API and worker boundary."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from takshyra.api import app
from takshyra.models import RecoveryOutcome, Run
from takshyra.worker import process_one
from tests.test_foundation import auth, pipeline_id

pytest_plugins = ("tests.test_foundation",)


def test_shadow_reprocess_requires_review_and_independent_recovery(local):
    settings, engine = local
    client = TestClient(app)
    headers, credentials = auth()
    pid = pipeline_id(client)
    source = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials,
                         json={"demo_fault": "F04"}).json()
    assert process_one(settings, "m8-source")
    incident = next(item for item in client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"]
                    if item["run_id"] == source["id"])
    route = f"/api/v1/incidents/{incident['id']}/shadow-replays"
    viewer_headers, viewer_credentials = auth("demo-a-viewer")
    other_headers, other_credentials = auth("demo-b-executor", "demo-b")
    assert client.post(route, headers=viewer_headers, auth=viewer_credentials).status_code == 403
    assert client.get(route, headers=other_headers, auth=other_credentials).status_code == 404
    replay_response = client.post(route, headers=headers, auth=credentials)
    assert replay_response.status_code == 201, replay_response.text
    replay = replay_response.json()
    assert (replay["status"], replay["baseline_row_count"], replay["replay_row_count"]) == ("SUPPORTED", 3, 4)
    assert client.post(route, headers=headers, auth=credentials).json()["id"] == replay["id"]
    assert not list(Path(settings.output_dir).glob("shadow-*"))

    headers["Idempotency-Key"] = "m8-reprocess-001"
    proposal = client.post("/api/v1/action-proposals", headers=headers, auth=credentials,
                           json={"action_type": "pipeline.reprocess_demo", "target_id": source["id"],
                                 "parameters": {"shadow_report_id": replay["id"]}}).json()
    assert (proposal["policy_decision"], proposal["status"]) == ("REQUIRES_APPROVAL", "AWAITING_APPROVAL")
    assert client.post(f"/api/v1/action-proposals/{proposal['id']}/execute", headers=headers, auth=credentials).status_code == 409
    approver_headers, approver_credentials = auth("demo-a-approver")
    assert client.post(f"/api/v1/action-proposals/{proposal['id']}/approve", headers=approver_headers,
                       auth=approver_credentials).status_code == 200
    executed = client.post(f"/api/v1/action-proposals/{proposal['id']}/execute", headers=headers, auth=credentials)
    assert executed.status_code == 200, executed.text
    assert executed.json()["verification_status"] == "VERIFIED"
    recovery_run_id = executed.json()["effect_ref_id"]
    verification_route = f"/api/v1/action-proposals/{proposal['id']}/verify-recovery"
    assert client.post(verification_route, headers=headers, auth=credentials).json()["status"] == "INCONCLUSIVE"
    assert process_one(settings, "m8-recovery")
    result = client.post(verification_route, headers=headers, auth=credentials)
    assert result.status_code == 200, result.text
    assert (result.json()["status"], result.json()["recovery_run_id"]) == ("VERIFIED", recovery_run_id)
    assert client.post(verification_route, headers=headers, auth=credentials).json()["id"] == result.json()["id"]
    assert client.get(f"/api/v1/incidents/{incident['id']}", headers=headers, auth=credentials).json()["status"] == "RESOLVED"
    with Session(engine) as db:
        assert db.get(Run, recovery_run_id).demo_fault is None
        assert db.get(RecoveryOutcome, result.json()["id"]).status == "VERIFIED"
    headers["Idempotency-Key"] = "m8-next-deficit-001"
    next_source = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials,
                              json={"demo_fault": "F04"}).json()
    assert process_one(settings, "m8-next-source")
    next_incident = next(item for item in client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"]
                         if item["run_id"] == next_source["id"])
    assert next_incident["error_code"] == incident["error_code"]
    assert next_incident["status"] == "OPEN"
    diagnosis = client.post(f"/api/v1/incidents/{next_incident['id']}/diagnoses", headers=headers,
                            auth=credentials).json()
    assert diagnosis["memory_status"] == "VERIFIED_CASES_AVAILABLE"
    assert diagnosis["similar_cases"][0]["id"] == result.json()["id"]


def test_reprocess_is_denied_without_supported_report(local):
    settings, engine = local
    client = TestClient(app)
    headers, credentials = auth()
    pid = pipeline_id(client)
    source = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials,
                         json={"demo_fault": "F04"}).json()
    assert process_one(settings, "m8-denial")
    incident = next(item for item in client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"]
                    if item["run_id"] == source["id"])
    headers["Idempotency-Key"] = "m8-invalid-001"
    denied = client.post("/api/v1/action-proposals", headers=headers, auth=credentials,
                         json={"action_type": "pipeline.reprocess_demo", "target_id": source["id"],
                               "parameters": {"shadow_report_id": "00000000-0000-0000-0000-000000000000"}})
    assert denied.status_code == 201 and denied.json()["policy_decision"] == "DENY"
    assert client.get(f"/api/v1/incidents/{incident['id']}", headers=headers, auth=credentials).json()["status"] == "OPEN"
    with Session(engine) as db:
        tenant_id = db.get(Run, source["id"]).tenant_id
    (Path(settings.output_dir) / tenant_id / source["id"] / "manifest.json").unlink()
    incomplete = client.post(f"/api/v1/incidents/{incident['id']}/shadow-replays", headers=headers,
                             auth=credentials)
    assert incomplete.status_code == 201 and incomplete.json()["status"] == "PARTIAL"
    fresh = client.post(f"/api/v1/demo/pipelines/{pid}/freshness-miss", headers=headers,
                        auth=credentials, json={}).json()
    unsupported = client.post(f"/api/v1/incidents/{fresh['id']}/shadow-replays", headers=headers,
                              auth=credentials)
    assert unsupported.status_code == 409  # No finished source run can be replayed.


def test_recovery_stays_open_when_output_manifest_is_invalid(local):
    settings, engine = local
    client = TestClient(app)
    headers, credentials = auth()
    pid = pipeline_id(client)
    source = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials,
                         json={"demo_fault": "F04"}).json()
    assert process_one(settings, "m8-invalid-source")
    incident = next(item for item in client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"]
                    if item["run_id"] == source["id"])
    replay = client.post(f"/api/v1/incidents/{incident['id']}/shadow-replays", headers=headers,
                         auth=credentials).json()
    headers["Idempotency-Key"] = "m8-invalid-output"
    proposal = client.post("/api/v1/action-proposals", headers=headers, auth=credentials,
                           json={"action_type": "pipeline.reprocess_demo", "target_id": source["id"],
                                 "parameters": {"shadow_report_id": replay["id"]}}).json()
    approver_headers, approver_credentials = auth("demo-a-approver")
    assert client.post(f"/api/v1/action-proposals/{proposal['id']}/approve", headers=approver_headers,
                       auth=approver_credentials).status_code == 200
    run = client.post(f"/api/v1/action-proposals/{proposal['id']}/execute", headers=headers,
                      auth=credentials).json()["effect_ref_id"]
    assert process_one(settings, "m8-invalid-recovery")
    with Session(engine) as db:
        tenant_id = db.get(Run, run).tenant_id
    (Path(settings.output_dir) / tenant_id / run / "manifest.json").unlink()
    outcome = client.post(f"/api/v1/action-proposals/{proposal['id']}/verify-recovery", headers=headers,
                          auth=credentials).json()
    assert outcome["status"] == "FAILED"
    assert client.get(f"/api/v1/incidents/{incident['id']}", headers=headers,
                      auth=credentials).json()["status"] == "OPEN"
