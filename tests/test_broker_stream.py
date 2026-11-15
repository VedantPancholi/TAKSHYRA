"""Checkpoint, replay and poison-envelope tests for local broker ingestion."""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import test_foundation as foundation
from takshyra.api import app
from takshyra.broker_stream import STREAM_KEY, consume_once
from takshyra.models import BrokerCheckpoint, BrokerEvent, Incident, Pipeline


@pytest.fixture
def seeded_local(tmp_path, monkeypatch):
    yield from foundation.local.__wrapped__(tmp_path, monkeypatch)


class FakeStream:
    def __init__(self, entries):
        self.entries = entries

    def xrange(self, _key, count):
        return self.entries[:count]

    def xread(self, keys, count, block):
        after = tuple(map(int, keys[STREAM_KEY].split("-")))
        items = [entry for entry in self.entries if tuple(map(int, entry[0].split("-"))) > after]
        return [(STREAM_KEY, items[:count])] if items else []


def message(index, tenant_id, pipeline_id, *, key=None, schema=14):
    payload = {
        "tenant_id": tenant_id, "pipeline_id": pipeline_id,
        "event_key": key or f"event-{index}", "schema": schema,
        "event_time": datetime.now(timezone.utc).isoformat(),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    return (f"{index}-0", {"payload": json.dumps(payload)})


def setup(db):
    pipeline = db.scalar(select(Pipeline).where(Pipeline.source_kind == "telemetry_demo_v1"))
    assert db.get(BrokerCheckpoint, STREAM_KEY).last_id == "0-0"
    return pipeline


def test_replay_deduplicates_and_records_dlq(seeded_local):
    _, engine = seeded_local
    with Session(engine) as db:
        pipeline = setup(db)
        stream = FakeStream([
            message(1, pipeline.tenant_id, pipeline.id),
            message(2, pipeline.tenant_id, pipeline.id, key="event-1"),
            message(3, pipeline.tenant_id, pipeline.id, schema=15),
        ])
        assert consume_once(stream, db) == 3
        assert db.get(BrokerCheckpoint, STREAM_KEY).last_id == "3-0"
        assert db.scalar(select(func.count()).select_from(BrokerEvent)) == 2
        assert db.scalar(select(func.count()).select_from(Incident).where(
            Incident.error_code == "STREAM_SCHEMA_INCOMPATIBLE")) == 1
        db.get(BrokerCheckpoint, STREAM_KEY).last_id = "0-0"
        db.commit()
        assert consume_once(stream, db) == 3
        assert db.scalar(select(func.count()).select_from(BrokerEvent)) == 2
        assert db.scalar(select(func.count()).select_from(Incident).where(
            Incident.error_code == "STREAM_SCHEMA_INCOMPATIBLE")) == 1


def test_bad_second_message_rolls_back_first_and_checkpoint(seeded_local):
    _, engine = seeded_local
    with Session(engine) as db:
        pipeline = setup(db)
        valid = message(1, pipeline.tenant_id, pipeline.id)
        stream = FakeStream([valid, ("2-0", {"payload": "{}"})])
        with pytest.raises(ValueError, match="Invalid broker payload"):
            consume_once(stream, db)
        db.rollback()
        assert db.scalar(select(func.count()).select_from(BrokerEvent)) == 0
        assert db.get(BrokerCheckpoint, STREAM_KEY).last_id == "0-0"
        stream.entries = [valid]
        assert consume_once(stream, db) == 1


def test_trimmed_checkpoint_refuses_silent_skip(seeded_local):
    _, engine = seeded_local
    with Session(engine) as db:
        pipeline = setup(db)
        db.get(BrokerCheckpoint, STREAM_KEY).last_id = "1-0"
        db.commit()
        stream = FakeStream([message(3, pipeline.tenant_id, pipeline.id)])
        with pytest.raises(RuntimeError, match="retention"):
            consume_once(stream, db)
        assert db.get(BrokerCheckpoint, STREAM_KEY).last_id == "1-0"


def test_broker_api_respects_roles_and_tenants(seeded_local, monkeypatch):
    _, engine = seeded_local
    captured = []
    monkeypatch.setattr("takshyra.streaming_api.redis_client", lambda: object())
    monkeypatch.setattr("takshyra.streaming_api.publish_fixture", lambda _redis, **kwargs:
                        captured.append(kwargs) or ["1-0"] * 4)
    client = TestClient(app)
    executor_headers, executor_auth = foundation.auth()
    viewer_headers, viewer_auth = foundation.auth("demo-a-viewer")
    route = "/api/v1/stream-observations/broker-demo"
    assert client.post(route, headers=viewer_headers, auth=viewer_auth,
                       json={"scenario": "CLEAN"}).status_code == 403
    assert client.post(route, headers=executor_headers, auth=executor_auth,
                       json={"scenario": "SINK_GAP"}).status_code == 422
    result = client.post(route, headers=executor_headers, auth=executor_auth,
                         json={"scenario": "CLEAN"})
    assert result.status_code == 202 and result.json()["queued"] == 4
    assert captured[0]["tenant_id"]
    with Session(engine) as db:
        pipeline = db.get(Pipeline, captured[0]["pipeline_id"])
        assert pipeline.tenant_id == captured[0]["tenant_id"]
    assert client.get("/api/v1/stream-observations/broker", headers=viewer_headers,
                      auth=viewer_auth).json()["written"] == 0
    other_headers, other_auth = foundation.auth("demo-b-viewer", "demo-b")
    assert client.get("/api/v1/stream-observations/broker", headers=other_headers,
                      auth=other_auth).json()["written"] == 0
