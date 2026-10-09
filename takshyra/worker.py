import logging
import socket
import time
import uuid
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from takshyra.config import Settings
from takshyra.db import engine
from takshyra.models import Attempt, AuditEvent, Pipeline, QualityResult, Run, now
from takshyra.runner import transform

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 2
LEASE_SECONDS = 300


def claim(db: Session, owner: str) -> tuple[str, str, int] | None:
    stmt = (
        select(Run)
        .where(or_(Run.status == "QUEUED", (Run.status == "RUNNING") & (Run.lease_until < now())))
        .order_by(Run.created_at)
        .limit(1)
    )
    if db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    run = db.scalar(stmt)
    if run is None:
        return None
    attempts = db.scalars(select(Attempt).where(Attempt.run_id == run.id).order_by(Attempt.number.desc())).all()
    if len(attempts) >= MAX_ATTEMPTS:
        run.status = "TIMED_OUT"
        run.error_code = "LEASE_EXHAUSTED"
        run.quality_status = "UNKNOWN"
        run.finished_at = now()
        db.commit()
        return None
    if attempts and attempts[0].status == "RUNNING":
        attempts[0].status = "TIMED_OUT"
        attempts[0].error_code = "LEASE_EXPIRED"
        attempts[0].finished_at = now()
    number = len(attempts) + 1
    run.status = "RUNNING"
    run.lease_owner = owner
    run.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
    db.add(Attempt(tenant_id=run.tenant_id, run_id=run.id, number=number, status="RUNNING"))
    db.commit()
    return run.id, run.tenant_id, number


def process_one(settings: Settings, owner: str | None = None) -> bool:
    owner = owner or f"{socket.gethostname()}:{uuid.uuid4()}"
    with Session(engine()) as db:
        claimed = claim(db, owner)
    if claimed is None:
        return False
    run_id, tenant_id, number = claimed
    result = None
    error_code = None
    try:
        with Session(engine()) as db:
            run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id))
            pipeline = db.scalar(select(Pipeline).where(Pipeline.id == run.pipeline_id, Pipeline.tenant_id == tenant_id))
            if pipeline is None or pipeline.source_kind != "seed_orders_v1":
                raise ValueError("PIPELINE_KIND_UNAVAILABLE")
        result = transform(settings.fixture_path, settings.output_dir, tenant_id, run_id)
    except ValueError as exc:
        error_code = str(exc) if str(exc).isupper() else "TRANSFORM_INVALID"
    except Exception:
        log.error("Run transformation failed for run %s", run_id)
        error_code = "TRANSFORM_FAILED"
    with Session(engine()) as db:
        run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update())
        if not run or run.status != "RUNNING" or run.lease_owner != owner:
            return True
        attempt = db.scalar(select(Attempt).where(Attempt.run_id == run_id, Attempt.number == number))
        attempt.finished_at = now()
        run.finished_at = now()
        run.lease_owner = None
        run.lease_until = None
        if error_code:
            run.status = attempt.status = "FAILED"
            run.error_code = attempt.error_code = error_code
            run.quality_status = "UNKNOWN"
            run.publication_status = "HELD"
        else:
            run.status = attempt.status = "SUCCEEDED"
            run.row_count = result["row_count"]
            run.quality_status = result["quality_status"]
            run.publication_status = "PUBLISHED" if result["quality_status"] == "PASS" else "QUARANTINED"
            run.manifest_path = str(__import__("pathlib").Path(settings.output_dir) / tenant_id / run_id / "manifest.json")
            for check in result["checks"]:
                db.add(QualityResult(tenant_id=tenant_id, run_id=run_id, rule_id=check["rule_id"], rule_version=1, outcome=check["outcome"], expected=check["expected"], observed=check["observed"]))
        enqueue_audit = db.scalar(select(AuditEvent).where(AuditEvent.tenant_id == tenant_id, AuditEvent.target_id == run_id, AuditEvent.action == "pipeline.run.enqueue"))
        if enqueue_audit:
            db.add(AuditEvent(tenant_id=tenant_id, actor_id=enqueue_audit.actor_id, action="pipeline.run.finish", target_id=run_id, outcome=run.status))
        db.commit()
    return True


def main():
    settings = Settings.from_env()
    logging.basicConfig(level=logging.INFO)
    while True:
        if not process_one(settings):
            # Redis is a wakeup optimization only. Always poll PostgreSQL after a bounded wait.
            try:
                import redis
                subscriber = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.5).pubsub()
                subscriber.subscribe("runs")
                subscriber.get_message(timeout=2)
                subscriber.close()
            except Exception:
                time.sleep(2)


if __name__ == "__main__":
    main()
