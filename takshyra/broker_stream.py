"""Local Redis Streams consumer with a transactional database checkpoint."""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from takshyra.db import engine
from takshyra.incidents import record_observation
from takshyra.models import BrokerCheckpoint, BrokerEvent, Pipeline, now

STREAM_KEY = "takshyra:telemetry:local:v1"
SCENARIOS = {"CLEAN", "SCHEMA_V15", "DUPLICATE", "LATE_EVENT", "CONSUMER_LAG"}


def redis_client() -> Redis:
    return Redis.from_url(os.environ["REDIS_URL"], decode_responses=True, socket_timeout=5)


def publish_fixture(redis: Redis, *, tenant_id: str, pipeline_id: str, scenario: str) -> list[str]:
    if scenario not in SCENARIOS:
        raise ValueError("Unknown broker scenario")
    at = now()
    keys = [uuid4().hex for _ in range(4)]
    if scenario == "DUPLICATE":
        keys.append(keys[1])
    pipe = redis.pipeline(transaction=True)
    for index, key in enumerate(keys):
        event_time = at - timedelta(seconds=100) if scenario == "LATE_EVENT" and index == 3 else at
        published_at = at - timedelta(seconds=120) if scenario == "CONSUMER_LAG" and index == 3 else at
        payload = {
            "tenant_id": tenant_id, "pipeline_id": pipeline_id, "event_key": key,
            "schema": 15 if scenario == "SCHEMA_V15" and index == 3 else 14,
            "event_time": event_time.isoformat(), "published_at": published_at.isoformat(),
        }
        pipe.xadd(STREAM_KEY, {"payload": json.dumps(payload, sort_keys=True)},
                  maxlen=10000, approximate=True)
    return pipe.execute()


def _stream_tuple(value: str) -> tuple[int, int]:
    left, right = value.split("-", 1)
    return int(left), int(right)


def consume_once(redis: Redis, db: Session, *, limit: int = 50) -> int:
    """Commit sink rows and checkpoint together; replay after a crash is idempotent."""
    if not 1 <= limit <= 100:
        raise ValueError("Invalid batch limit")
    # PostgreSQL serializes concurrent consumers on this row. The row is installed by migration.
    checkpoint = db.scalar(select(BrokerCheckpoint).where(
        BrokerCheckpoint.stream_key == STREAM_KEY,
    ).with_for_update())
    if checkpoint is None:
        raise RuntimeError("Broker checkpoint missing; run migrations")
    first = redis.xrange(STREAM_KEY, count=1)
    if checkpoint.last_id != "0-0" and first and _stream_tuple(first[0][0]) > _stream_tuple(checkpoint.last_id):
        raise RuntimeError("Broker retention passed checkpoint; manual reconciliation required")
    response = redis.xread({STREAM_KEY: checkpoint.last_id}, count=limit, block=1000)
    if not response:
        return 0
    entries = response[0][1]
    for stream_id, fields in entries:
        if set(fields) != {"payload"}:
            raise ValueError("Invalid broker envelope")
        item = json.loads(fields["payload"])
        if not isinstance(item, dict) or set(item) != {
            "tenant_id", "pipeline_id", "event_key", "schema", "event_time", "published_at",
        }:
            raise ValueError("Invalid broker payload")
        if not all(isinstance(item[field], str) and 0 < len(item[field]) <= 64 for field in (
            "tenant_id", "pipeline_id", "event_key",
        )) or type(item["schema"]) is not int:
            raise ValueError("Invalid broker event fields")
        event_time = datetime.fromisoformat(item["event_time"])
        published_at = datetime.fromisoformat(item["published_at"])
        if event_time.tzinfo is None or published_at.tzinfo is None:
            raise ValueError("Broker timestamps must include timezone")
        pipeline = db.scalar(select(Pipeline).where(
            Pipeline.id == item["pipeline_id"], Pipeline.tenant_id == item["tenant_id"],
            Pipeline.source_kind == "telemetry_demo_v1",
        ))
        if pipeline is None:
            raise ValueError("Broker event has no bound local pipeline")
        existing = db.scalar(select(BrokerEvent.id).where(
            BrokerEvent.tenant_id == item["tenant_id"],
            BrokerEvent.pipeline_id == item["pipeline_id"],
            BrokerEvent.event_key == item["event_key"],
        ))
        if existing is None:
            age = (now() - published_at.astimezone(timezone.utc)).total_seconds()
            lateness = (published_at - event_time).total_seconds()
            reason = ("STREAM_SCHEMA_INCOMPATIBLE" if item["schema"] != 14 else
                      "STREAM_CONSUMER_LAG" if age > 60 else
                      "STREAM_LATE_EVENT" if lateness > 60 else None)
            outcome = "DLQ" if item["schema"] != 14 else "WRITTEN"
            event = BrokerEvent(
                tenant_id=item["tenant_id"], pipeline_id=item["pipeline_id"],
                stream_id=stream_id, event_key=item["event_key"], outcome=outcome,
                reason=reason, event_time=event_time,
            )
            db.add(event)
            db.flush()
            if reason:
                record_observation(
                    db, tenant_id=item["tenant_id"], pipeline_id=item["pipeline_id"],
                    category="QUALITY_FAILURE", severity="HIGH" if outcome == "DLQ" else "MEDIUM",
                    error_code=reason, source_kind="BROKER_EVENT", source_id=event.id,
                    provenance="simulated",
                )
        checkpoint.last_id = stream_id
        checkpoint.updated_at = now()
    db.commit()
    return len(entries)


def run_forever() -> None:
    redis = redis_client()
    factory = sessionmaker(engine(), expire_on_commit=False)
    while True:
        try:
            with factory() as db:
                consume_once(redis, db)
        except Exception:
            # Leave checkpoint untouched; malformed envelopes require operator review.
            import logging
            logging.exception("Broker poll failed")
            time.sleep(2)


if __name__ == "__main__":
    run_forever()
