import json
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from takshyra import db
from takshyra.api import app
from takshyra.auth import hash_password
from takshyra.config import Settings
from takshyra.models import Attempt, Membership, Pipeline, QualityResult, Run, User, now
from takshyra.runner import read_manifest, transform
from takshyra.seed import seed
from takshyra.worker import claim, process_one

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def local(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "development")
    for index, name in enumerate(("A_EXECUTOR", "A_VIEWER", "B_EXECUTOR", "B_VIEWER")):
        monkeypatch.setenv(f"DEMO_{name}_PASSWORD", f"local-password-{index}-123456789")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("FIXTURE_PATH", str(ROOT / "seed" / "synthetic_orders.csv"))
    engine = create_engine(url)
    monkeypatch.setattr(db, "_engine", engine)
    from takshyra import worker

    monkeypatch.setattr(worker, "engine", lambda: engine)
    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    seed()
    yield Settings.from_env(), engine
    engine.dispose()


def auth(user="demo-a-executor", tenant="demo-a"):
    passwords = {"demo-a-executor": "local-password-0-123456789", "demo-a-viewer": "local-password-1-123456789", "demo-b-executor": "local-password-2-123456789", "demo-b-viewer": "local-password-3-123456789"}
    return {"X-Tenant-Slug": tenant, "Idempotency-Key": "stable-key-001"}, (user, passwords[user])


def pipeline_id(client, user="demo-a-executor", tenant="demo-a"):
    headers, credentials = auth(user, tenant)
    response = client.get("/api/v1/pipelines", headers=headers, auth=credentials)
    assert response.status_code == 200
    return response.json()["items"][0]["id"]


def test_migration_seed_auth_and_worker(local):
    settings, engine = local
    client = TestClient(app)
    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").status_code == 200
    assert client.get("/api/v1/pipelines").status_code == 401
    headers, credentials = auth()
    assert client.get("/api/v1/me", headers=headers, auth=credentials).json()["role"] == "executor"
    pid = pipeline_id(client)
    queued = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={})
    assert queued.status_code == 202
    run_id = queued.json()["id"]
    assert queued.json()["execution_status"] == "QUEUED"
    assert process_one(settings, "test-worker")
    completed = client.get(f"/api/v1/runs/{run_id}", headers=headers, auth=credentials)
    assert completed.status_code == 200
    result = completed.json()
    assert (result["execution_status"], result["quality_status"], result["publication_status"]) == ("SUCCEEDED", "PASS", "PUBLISHED")
    assert result["row_count"] == 4
    assert len(result["quality_results"]) == 3
    with Session(engine) as session:
        run = session.get(Run, run_id)
        assert read_manifest(settings.output_dir, run.tenant_id, run_id)["row_count"] == 4
        assert session.scalar(select(QualityResult).where(QualityResult.run_id == run_id))
    assert not process_one(settings, "test-worker")


def test_authorization_and_idempotency(local):
    _, engine = local
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    viewer_headers, viewer_credentials = auth("demo-a-viewer")
    assert client.post(f"/api/v1/pipelines/{pid}/runs", headers=viewer_headers, auth=viewer_credentials, json={}).status_code == 403
    assert client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=("demo-a-executor", viewer_credentials[1]), json={}).status_code == 401
    assert client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=("demo-a-executor", "wrong"), json={}).status_code == 401
    first = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={})
    assert first.status_code == 202
    again = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={})
    assert again.json()["id"] == first.json()["id"]
    with Session(engine) as session:
        second_pipeline = Pipeline(tenant_id=session.get(Run, first.json()["id"]).tenant_id, name="orders_copy_v1", source_kind="seed_orders_v1")
        session.add(second_pipeline)
        session.commit()
        second_id = second_pipeline.id
    conflict = client.post(f"/api/v1/pipelines/{second_id}/runs", headers=headers, auth=credentials, json={})
    assert conflict.status_code == 409
    other_id = pipeline_id(client, "demo-b-executor", "demo-b")
    wrong_payload = client.post(f"/api/v1/pipelines/{other_id}/runs", headers=headers, auth=credentials, json={})
    assert wrong_payload.status_code == 404
    assert client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={"tenant_id": "demo-b"}).status_code == 422
    b_headers, b_credentials = auth("demo-b-executor", "demo-b")
    assert client.get(f"/api/v1/runs/{first.json()['id']}", headers=b_headers, auth=b_credentials).status_code == 404
    assert client.get("/api/v1/pipelines", headers={"X-Tenant-Slug": "demo-b"}, auth=credentials).status_code == 403
    with Session(engine) as session:
        assert len(session.scalars(select(Run)).all()) == 1


def test_failure_and_crash_reconciliation(local, tmp_path, caplog):
    settings, engine = local
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    run_id = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={}).json()["id"]
    with Session(engine) as session:
        claimed = claim(session, "crashed-worker")
        run = session.get(Run, run_id)
        transform(settings.fixture_path, settings.output_dir, run.tenant_id, run_id)
        manifest = Path(settings.output_dir) / run.tenant_id / run_id / "manifest.json"
        original_mtime = manifest.stat().st_mtime_ns
        run.lease_until = now() - timedelta(seconds=1)
        session.commit()
    assert claimed[0] == run_id
    assert process_one(settings, "replacement-worker")
    assert manifest.stat().st_mtime_ns == original_mtime
    with Session(engine) as session:
        run = session.get(Run, run_id)
        assert run.status == "SUCCEEDED"
        assert [a.status for a in session.scalars(select(Attempt).where(Attempt.run_id == run_id).order_by(Attempt.number))] == ["TIMED_OUT", "SUCCEEDED"]
    headers["Idempotency-Key"] = "another-key-001"
    failed_id = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={}).json()["id"]
    bad_settings = Settings(settings.app_env, settings.database_url, settings.redis_url, settings.output_dir, str(tmp_path / "missing.csv"), settings.demo_passwords)
    assert process_one(bad_settings, "failure-worker")
    assert settings.demo_passwords["demo-a-executor"] not in caplog.text
    with Session(engine) as session:
        failed = session.get(Run, failed_id)
        assert (failed.status, failed.quality_status, failed.publication_status, failed.error_code) == ("FAILED", "UNKNOWN", "HELD", "SOURCE_UNAVAILABLE_OR_TOO_LARGE")


def test_quality_failure_quarantines(local, tmp_path):
    settings, engine = local
    source = tmp_path / "bad.csv"
    source.write_text("order_id,order_ts,amount,customer_id\nord-1,2026-01-01T00:00:00Z,1,\n", encoding="utf-8")
    bad_settings = Settings(settings.app_env, settings.database_url, settings.redis_url, settings.output_dir, str(source), settings.demo_passwords)
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    run_id = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={}).json()["id"]
    assert process_one(bad_settings, "quality-worker")
    with Session(engine) as session:
        run = session.get(Run, run_id)
        assert (run.status, run.quality_status, run.publication_status) == ("SUCCEEDED", "FAIL", "QUARANTINED")


def test_production_demo_auth_rejected(local, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        Settings.from_env()
    client = TestClient(app)
    headers, credentials = auth()
    assert client.get("/api/v1/pipelines", headers=headers, auth=credentials).status_code == 503


def test_transient_fault_retries_twice_then_succeeds(local):
    settings, engine = local
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    response = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={"demo_fault": "F02"})
    assert response.status_code == 202
    run_id = response.json()["id"]
    for number in (1, 2):
        assert process_one(settings, f"retry-{number}")
        with Session(engine) as session:
            run = session.get(Run, run_id)
            assert run.status == "QUEUED"
            assert run.next_attempt_at is not None
            assert len(session.scalars(select(Attempt).where(Attempt.run_id == run_id)).all()) == number
        assert not process_one(settings, "too-early")
        with Session(engine) as session:
            run = session.get(Run, run_id)
            run.next_attempt_at = now() - timedelta(seconds=1)
            session.commit()
    assert process_one(settings, "retry-3")
    completed = client.get(f"/api/v1/runs/{run_id}", headers=headers, auth=credentials).json()
    assert (completed["execution_status"], completed["quality_status"], completed["publication_status"]) == ("SUCCEEDED", "PASS", "PUBLISHED")
    assert [attempt["status"] for attempt in completed["attempts"]] == ["FAILED", "FAILED", "SUCCEEDED"]
    assert client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"] == []


def test_persistent_fault_caps_attempts_and_deduplicates(local):
    settings, engine = local
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    incident_id = None
    for run_number in (1, 2):
        headers["Idempotency-Key"] = f"persistent-{run_number:03d}"
        queued = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={"demo_fault": "F03"})
        assert queued.status_code == 202
        run_id = queued.json()["id"]
        for attempt in (1, 2, 3):
            assert process_one(settings, f"persistent-{run_number}-{attempt}")
            if attempt < 3:
                with Session(engine) as session:
                    run = session.get(Run, run_id)
                    assert run.status == "QUEUED"
                    run.next_attempt_at = now() - timedelta(seconds=1)
                    session.commit()
        result = client.get(f"/api/v1/runs/{run_id}", headers=headers, auth=credentials).json()
        assert result["execution_status"] == "FAILED"
        assert result["quality_status"] == "UNKNOWN"
        assert len(result["attempts"]) == 3
        items = client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"]
        assert len(items) == 1
        assert items[0]["occurrence_count"] == run_number
        assert items[0]["provenance"] == "simulated"
        incident_id = items[0]["id"]
    detail = client.get(f"/api/v1/incidents/{incident_id}", headers=headers, auth=credentials).json()
    assert len(detail["timeline"]) == 2
    assert {event["source_kind"] for event in detail["timeline"]} == {"RUN"}
    assert detail["diagnosis_status"] == "UNKNOWN"


def test_row_drop_incident_evidence_and_authorization(local, tmp_path):
    settings, engine = local
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    run_id = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={"demo_fault": "F04"}).json()["id"]
    assert process_one(settings, "row-drop-worker")
    run = client.get(f"/api/v1/runs/{run_id}", headers=headers, auth=credentials).json()
    assert (run["execution_status"], run["quality_status"], run["publication_status"], run["row_count"]) == ("SUCCEEDED", "FAIL", "QUARANTINED", 3)
    incident = client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"][0]
    assert (incident["category"], incident["status"], incident["provenance"]) == ("QUALITY_FAILURE", "OPEN", "simulated")
    detail = client.get(f"/api/v1/incidents/{incident['id']}", headers=headers, auth=credentials).json()
    serialized = json.dumps(detail)
    assert settings.demo_passwords["demo-a-executor"] not in serialized
    assert settings.fixture_path not in serialized
    evidence = [event for event in detail["timeline"] if event["source_kind"] == "QUALITY_RESULT"]
    assert len(evidence) == 1
    with Session(engine) as session:
        assert session.get(QualityResult, evidence[0]["source_id"]).outcome == "FAIL"
    viewer_headers, viewer_credentials = auth("demo-a-viewer")
    assert client.get(f"/api/v1/incidents/{incident['id']}", headers=viewer_headers, auth=viewer_credentials).status_code == 200
    assert client.patch(f"/api/v1/incidents/{incident['id']}", headers=viewer_headers, auth=viewer_credentials, json={"status": "INVESTIGATING"}).status_code == 403
    b_headers, b_credentials = auth("demo-b-executor", "demo-b")
    assert client.get(f"/api/v1/incidents/{incident['id']}", headers=b_headers, auth=b_credentials).status_code == 404
    assert client.patch(f"/api/v1/incidents/{incident['id']}", headers=b_headers, auth=b_credentials, json={"status": "INVESTIGATING"}).status_code == 404
    assert client.patch(f"/api/v1/incidents/{incident['id']}", headers=headers, auth=credentials, json={"status": "RESOLVED"}).status_code == 422
    investigated = client.patch(f"/api/v1/incidents/{incident['id']}", headers=headers, auth=credentials, json={"status": "INVESTIGATING"})
    assert investigated.status_code == 200
    assert investigated.json()["status"] == "INVESTIGATING"
    assert investigated.json()["timeline"][-1]["kind"] == "STATUS_CHANGED"
    assert investigated.json()["owner_id"] is not None
    with Session(engine) as session:
        second = User(username="demo-a-second-executor", password_hash=hash_password("second-local-password-123456"))
        session.add(second)
        session.flush()
        session.add(Membership(tenant_id=session.get(Run, run_id).tenant_id, user_id=second.id, role="executor"))
        session.commit()
    second_headers = {"X-Tenant-Slug": "demo-a"}
    second_credentials = ("demo-a-second-executor", "second-local-password-123456")
    assert client.get(f"/api/v1/incidents/{incident['id']}", headers=second_headers, auth=second_credentials).status_code == 200
    assert client.patch(f"/api/v1/incidents/{incident['id']}", headers=second_headers, auth=second_credentials, json={"status": "INVESTIGATING"}).status_code == 403
    bad_source = tmp_path / "null_customer.csv"
    bad_source.write_text("order_id,order_ts,amount,customer_id\nord-1,2026-01-01T00:00:00Z,1,\n", encoding="utf-8")
    null_settings = Settings(settings.app_env, settings.database_url, settings.redis_url, settings.output_dir, str(bad_source), settings.demo_passwords)
    headers["Idempotency-Key"] = "different-quality-001"
    second_run = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={})
    assert second_run.status_code == 202
    assert process_one(null_settings, "null-quality-worker")
    items = client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"]
    assert len(items) == 2
    assert {item["error_code"] for item in items} == {"QUALITY_SOURCE_ROW_COUNT_MATCH", "QUALITY_CUSTOMER_ID_NULL_0"}


def test_freshness_miss_without_run_deduplicates(local):
    _, engine = local
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    viewer_headers, viewer_credentials = auth("demo-a-viewer")
    route = f"/api/v1/demo/pipelines/{pid}/freshness-miss"
    assert client.post(route, headers=viewer_headers, auth=viewer_credentials).status_code == 403
    first = client.post(route, headers=headers, auth=credentials)
    second = client.post(route, headers=headers, auth=credentials)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["run_id"] is None
    assert second.json()["occurrence_count"] == 2
    assert second.json()["provenance"] == "simulated"
    assert len(second.json()["timeline"]) == 2
    with Session(engine) as session:
        assert len(session.scalars(select(Run)).all()) == 0
    b_headers, b_credentials = auth("demo-b-executor", "demo-b")
    assert client.post(route, headers=b_headers, auth=b_credentials).status_code == 404
    assert client.post(route, headers=headers, auth=credentials, json={"error_code": "FORGED"}).status_code == 422


def test_expired_leases_stop_and_open_incident(local):
    _, engine = local
    client = TestClient(app)
    pid = pipeline_id(client)
    headers, credentials = auth()
    run_id = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials, json={}).json()["id"]
    for number in (1, 2, 3):
        with Session(engine) as session:
            claimed = claim(session, f"expired-{number}")
            assert claimed == (run_id, session.get(Run, run_id).tenant_id, number)
            run = session.get(Run, run_id)
            run.lease_until = now() - timedelta(seconds=1)
            session.commit()
    with Session(engine) as session:
        assert claim(session, "expired-final") is None
        run = session.get(Run, run_id)
        assert (run.status, run.error_code, run.quality_status) == ("TIMED_OUT", "LEASE_EXHAUSTED", "UNKNOWN")
        attempts = session.scalars(select(Attempt).where(Attempt.run_id == run_id).order_by(Attempt.number)).all()
        assert [attempt.status for attempt in attempts] == ["TIMED_OUT"] * 3
    incidents = client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"]
    assert len(incidents) == 1
    assert incidents[0]["error_code"] == "LEASE_EXHAUSTED"
