import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.adf import AdfObserver, AdfScope
from takshyra.adf_ingestion import ingest_runs, register_binding
from takshyra.api import app
from takshyra.models import AdfPipelineBinding, AdfRunObservation, Incident, IncidentEvent, Tenant
import test_foundation as foundation


@pytest.fixture
def local(tmp_path, monkeypatch):
    yield from foundation.local.__wrapped__(tmp_path, monkeypatch)


def sample(run_id="run-1", status="Failed"):
    return {
        "value": [{
            "runId": run_id, "pipelineName": "orders-adf", "status": status,
            "runStart": "2026-11-15T10:00:00Z", "runEnd": "2026-11-15T10:02:00Z",
            "parameters": {"password": "must-never-be-stored"}, "message": "must-never-be-stored",
        }],
    }


def setup(db):
    tenant = db.scalar(select(Tenant).where(Tenant.slug == "demo-a"))
    scope = AdfScope(tenant.id, "00000000-0000-0000-0000-000000000001", "rg-test", "factory-test")
    binding = register_binding(
        db, scope=scope, local_name="orders_adf_local", external_name="orders-adf",
    )
    return scope, binding


def observed(scope, response):
    observer = AdfObserver(
        tenant_id=scope.tenant_id, allowed_targets=frozenset({scope.target}),
        transport=lambda _url, _body: response,
    )
    until = datetime.now(timezone.utc)
    return observer.query(scope, until - timedelta(hours=1), until)


def test_adf_ingestion_is_tenant_scoped_redacted_and_idempotent(local):
    _, engine = local
    with Session(engine) as db:
        scope, binding = setup(db)
        result = observed(scope, sample())
        assert ingest_runs(db, scope=scope, binding=binding, result=result,
                           provenance="simulated") == {
            "created": 1, "updated": 0, "incidents": 1, "skipped": 0,
        }
        db.commit()
        assert ingest_runs(db, scope=scope, binding=binding, result=result,
                           provenance="simulated") == {
            "created": 0, "updated": 1, "incidents": 0, "skipped": 0,
        }
        db.commit()
        rows = db.scalars(select(AdfRunObservation)).all()
        events = db.scalars(select(IncidentEvent).where(
            IncidentEvent.source_kind == "ADF_RUN_OBSERVATION",
        )).all()
        incidents = db.scalars(select(Incident).where(
            Incident.error_code == "ADF_RUN_FAILED",
        )).all()
        assert len(rows) == len(events) == len(incidents) == 1
        assert events[0].source_id == rows[0].id
        assert incidents[0].provenance == "simulated"
        assert "must-never-be-stored" not in str(rows[0].__dict__)

    client = TestClient(app)
    a_headers, a_credentials = foundation.auth("demo-a-viewer")
    b_headers, b_credentials = foundation.auth("demo-b-viewer", "demo-b")
    response = client.get("/api/v1/adf-observations", headers=a_headers, auth=a_credentials)
    assert response.status_code == 200
    assert response.json()["items"][0]["external_run_id"] == "run-1"
    assert response.json()["items"][0]["provenance"] == "simulated"
    assert client.get("/api/v1/adf-observations", headers=b_headers,
                      auth=b_credentials).json() == {"items": []}
    incident_list = client.get("/api/v1/incidents", headers=a_headers, auth=a_credentials)
    assert any(item["error_code"] == "ADF_RUN_FAILED" for item in incident_list.json()["items"])


def test_adf_run_status_transition_and_binding_guard(local):
    _, engine = local
    with Session(engine) as db:
        scope, binding = setup(db)
        assert ingest_runs(db, scope=scope, binding=binding,
                           result=observed(scope, sample(status="InProgress")),
                           provenance="simulated")["incidents"] == 0
        assert ingest_runs(db, scope=scope, binding=binding,
                           result=observed(scope, sample(status="Failed")),
                           provenance="simulated")["incidents"] == 1
        with pytest.raises(ValueError, match="terminal"):
            ingest_runs(db, scope=scope, binding=binding,
                        result=observed(scope, sample(status="Succeeded")),
                        provenance="simulated")
        with pytest.raises(ValueError, match="bound"):
            register_binding(db, scope=scope, local_name="orders_adf_local",
                             external_name="other-pipeline")
        with pytest.raises(ValueError, match="already bound"):
            register_binding(db, scope=scope, local_name="another_local",
                             external_name="orders-adf")
        db.rollback()


def test_adf_ingestion_rejects_incomplete_or_cross_tenant_results(local):
    _, engine = local
    with Session(engine) as db:
        scope, binding = setup(db)
        result = observed(scope, sample())
        with pytest.raises(ValueError, match="complete"):
            ingest_runs(db, scope=scope, binding=binding,
                        result={**result, "truncated": True}, provenance="simulated")
        wrong = {**result, "items": [{**result["items"][0], "tenant_id": "other"}]}
        with pytest.raises(PermissionError, match="allowlist"):
            ingest_runs(db, scope=scope, binding=binding, result=wrong,
                        provenance="simulated")
        assert db.scalars(select(AdfRunObservation)).all() == []


def test_late_invalid_run_cannot_leave_partial_incident_after_commit(local):
    _, engine = local
    with Session(engine) as db:
        scope, binding = setup(db)
        db.commit()
        first = observed(scope, sample(run_id="good-first"))["items"][0]
        second = {**first, "run_id": "bad-second", "run_end": "not-a-timestamp"}
        with pytest.raises(ValueError, match="timestamp"):
            ingest_runs(db, scope=scope, binding=binding,
                        result={"items": [first, second], "truncated": False},
                        provenance="simulated")
        db.commit()  # A caller catching the error must not commit the first item.
        assert db.scalars(select(AdfRunObservation)).all() == []
        assert db.scalars(select(Incident).where(Incident.error_code == "ADF_RUN_FAILED")).all() == []


def test_duplicate_batch_and_malformed_fields_roll_back_every_item(local):
    _, engine = local
    with Session(engine) as db:
        scope, binding = setup(db)
        db.commit()
        valid = observed(scope, sample(run_id="first"))["items"][0]
        bad_cases = [
            {**valid, "run_id": "first"},
            {**valid, "run_id": "second", "status": {"untrusted": "value"}},
            {**valid, "run_id": "second", "run_start": "2026-11-15T10:00:00"},
            {**valid, "run_id": "second", "run_end": "2026-11-15T09:00:00Z"},
            {**valid, "run_id": "second", "run_end": "x" * 65},
            {**valid, "run_id": "second", "factory": "another-factory"},
        ]
        for bad in bad_cases:
            with pytest.raises((ValueError, PermissionError)):
                ingest_runs(db, scope=scope, binding=binding,
                            result={"items": [valid, bad], "truncated": False},
                            provenance="simulated")
            db.commit()
            assert db.scalars(select(AdfRunObservation)).all() == []
            assert db.scalars(select(IncidentEvent).where(
                IncidentEvent.source_kind == "ADF_RUN_OBSERVATION",
            )).all() == []
        with pytest.raises(ValueError, match="complete"):
            ingest_runs(db, scope=scope, binding=binding,
                        result={"items": [valid] * 101, "truncated": False},
                        provenance="simulated")


def test_ingestion_requires_a_persisted_exact_binding(local):
    _, engine = local
    with Session(engine) as db:
        scope, binding = setup(db)
        db.commit()
        forged = AdfPipelineBinding(
            id=str(uuid.uuid4()), tenant_id=binding.tenant_id,
            pipeline_id=binding.pipeline_id, factory=binding.factory,
            external_name=binding.external_name,
        )
        with pytest.raises(PermissionError, match="binding"):
            ingest_runs(db, scope=scope, binding=forged,
                        result=observed(scope, sample()), provenance="simulated")
        db.commit()
        assert db.scalars(select(AdfRunObservation)).all() == []


def test_two_failed_runs_add_two_evidence_events_without_duplicate_repolls(local):
    _, engine = local
    with Session(engine) as db:
        scope, binding = setup(db)
        db.commit()
        first = observed(scope, sample(run_id="first"))["items"][0]
        second = {**first, "run_id": "second"}
        result = {"items": [first, second], "truncated": False}
        assert ingest_runs(db, scope=scope, binding=binding, result=result,
                           provenance="simulated")["incidents"] == 2
        db.commit()
        assert ingest_runs(db, scope=scope, binding=binding, result=result,
                           provenance="simulated")["incidents"] == 0
        db.commit()
        incident = db.scalar(select(Incident).where(Incident.error_code == "ADF_RUN_FAILED"))
        events = db.scalars(select(IncidentEvent).where(
            IncidentEvent.source_kind == "ADF_RUN_OBSERVATION",
        )).all()
        assert incident.occurrence_count == 2
        assert len(events) == 2
        assert {event.source_id for event in events} == {
            row.id for row in db.scalars(select(AdfRunObservation)).all()
        }
