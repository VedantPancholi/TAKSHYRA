from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.adf import AdfObserver, AdfScope
from takshyra.api import app
from takshyra.models import Incident, StreamObservation
from takshyra.streaming import evaluate
import test_foundation as foundation


@pytest.fixture
def seeded_local(tmp_path, monkeypatch):
    yield from foundation.local.__wrapped__(tmp_path, monkeypatch)


@pytest.mark.parametrize("scenario,code", [
    ("CLEAN", None), ("DUPLICATE", None),
    ("SCHEMA_V15", "STREAM_SCHEMA_INCOMPATIBLE"),
    ("SINK_GAP", "STREAM_RECONCILIATION_GAP"),
    ("CONSUMER_LAG", "STREAM_CONSUMER_LAG"),
    ("LATE_EVENT", "STREAM_LATE_EVENT"),
])
def test_stream_scenarios_are_deterministic(scenario, code):
    first = evaluate(scenario)
    assert first == evaluate(scenario)
    assert first[1] == code
    assert first[2]["source_sink_gap"] == (1 if scenario in {"SCHEMA_V15", "SINK_GAP"} else 0)
    if scenario == "DUPLICATE":
        assert first[2]["duplicates"] == 1 and first[2]["written"] == 4


def test_stream_api_persists_evidence_and_respects_tenant_roles(seeded_local):
    _, engine = seeded_local
    client = TestClient(app)
    headers, credentials = foundation.auth()
    viewer_headers, viewer_credentials = foundation.auth("demo-a-viewer")
    route = "/api/v1/stream-observations/demo"
    assert client.post(route, headers=viewer_headers, auth=viewer_credentials,
                       json={"scenario": "SINK_GAP"}).status_code == 403
    assert client.post(route, headers=headers, auth=credentials,
                       json={"scenario": "SINK_GAP", "path": "/tmp/private"}).status_code == 422
    result = client.post(route, headers=headers, auth=credentials, json={"scenario": "SINK_GAP"})
    assert result.status_code == 201
    body = result.json()
    assert body["metrics"]["source_sink_gap"] == 1
    assert body["incident_id"] and body["provenance"] == "simulated"
    assert client.get("/api/v1/stream-observations", headers=viewer_headers,
                      auth=viewer_credentials).json()["items"][0]["id"] == body["id"]
    b_headers, b_credentials = foundation.auth("demo-b-viewer", "demo-b")
    assert client.get("/api/v1/stream-observations", headers=b_headers,
                      auth=b_credentials).json() == {"items": []}
    with Session(engine) as db:
        row = db.scalar(select(StreamObservation).where(StreamObservation.id == body["id"]))
        incident = db.scalar(select(Incident).where(Incident.id == body["incident_id"]))
        assert row.tenant_id == incident.tenant_id
        assert incident.error_code == "STREAM_RECONCILIATION_GAP"


def test_adf_mock_is_read_only_bounded_and_redacted():
    scope = AdfScope("tenant-a", "00000000-0000-0000-0000-000000000001", "rg-test", "factory-test")
    calls = []

    def transport(url, body):
        calls.append((url, body))
        if len(calls) == 1:
            return {"value": [{"runId": "r1", "pipelineName": "orders", "status": "Failed",
                               "parameters": {"password": "secret"}, "message": "secret"}],
                    "continuationToken": "page-2"}
        return {"value": [{"runId": "r2", "pipelineName": "orders", "status": "Succeeded"}]}

    observer = AdfObserver(tenant_id="tenant-a", allowed_targets=frozenset({scope.target}), transport=transport)
    until = datetime.now(timezone.utc)
    result = observer.query(scope, until - timedelta(hours=1), until)
    assert result["pages"] == 2 and not result["truncated"]
    assert [row["run_id"] for row in result["items"]] == ["r1", "r2"]
    assert "secret" not in str(result)
    assert all(url == scope.url and set(body) <= {"lastUpdatedAfter", "lastUpdatedBefore", "continuationToken"}
               for url, body in calls)
    with pytest.raises(PermissionError):
        AdfObserver(tenant_id="tenant-b", allowed_targets=frozenset({scope.target}),
                    transport=transport).query(scope, until - timedelta(hours=1), until)
    with pytest.raises(ValueError):
        observer.query(scope, until - timedelta(days=2), until)
    assert len(calls) == 2


def test_adf_mock_rejects_repeated_cursor_and_caps_output():
    scope = AdfScope("tenant-a", "00000000-0000-0000-0000-000000000001", "rg-test", "factory-test")
    until = datetime.now(timezone.utc)

    def repeated(_url, _body):
        return {"value": [], "continuationToken": "same"}

    observer = AdfObserver(tenant_id="tenant-a", allowed_targets=frozenset({scope.target}), transport=repeated)
    with pytest.raises(ValueError, match="continuation"):
        observer.query(scope, until - timedelta(minutes=1), until)

    def oversized(_url, _body):
        return {"value": [{"runId": str(i), "pipelineName": "orders", "status": "Succeeded"}
                          for i in range(4)]}

    observer = AdfObserver(tenant_id="tenant-a", allowed_targets=frozenset({scope.target}), transport=oversized)
    result = observer.query(scope, until - timedelta(minutes=1), until, limit=2)
    assert len(result["items"]) == 2 and result["truncated"]
