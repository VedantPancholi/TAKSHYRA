import hashlib
import json
import logging
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from takshyra.auth import Identity, executor, identity
from takshyra.config import Settings
from takshyra.db import session
from takshyra.models import Attempt, AuditEvent, Pipeline, QualityResult, Run

app = FastAPI(title="Takshyra Data Reliability Platform", version="0.1.0")
log = logging.getLogger(__name__)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    correlation_id = str(uuid.uuid4())
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail), "correlation_id": correlation_id, "details": []}},
        headers=exc.headers,
    )


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # No path, code, SQL, tenant, approval or role fields accepted.
    parameters: dict[str, str] = Field(default_factory=dict, max_length=0)


@app.get("/health/live")
def live():
    return {"status": "live"}


@app.get("/health/ready")
def ready(db: Session = Depends(session)):
    try:
        Settings.from_env()
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Service unavailable") from None


@app.get("/api/v1/me")
def me(principal: Identity = Depends(identity)):
    return {"username": principal.username, "tenant_slug": principal.tenant_slug, "role": principal.role}


@app.get("/api/v1/pipelines")
def pipelines(principal: Identity = Depends(identity), db: Session = Depends(session)):
    rows = db.scalars(select(Pipeline).where(Pipeline.tenant_id == principal.tenant_id).order_by(Pipeline.name).limit(100)).all()
    return {"items": [{"id": row.id, "name": row.name, "source_kind": row.source_kind} for row in rows]}


def run_view(db: Session, run: Run) -> dict:
    attempts = db.scalars(select(Attempt).where(Attempt.tenant_id == run.tenant_id, Attempt.run_id == run.id).order_by(Attempt.number)).all()
    checks = db.scalars(select(QualityResult).where(QualityResult.tenant_id == run.tenant_id, QualityResult.run_id == run.id).order_by(QualityResult.rule_id)).all()
    return {
        "id": run.id, "pipeline_id": run.pipeline_id, "execution_status": run.status,
        "quality_status": run.quality_status, "publication_status": run.publication_status,
        "row_count": run.row_count, "manifest_path": run.manifest_path,
        "error_code": run.error_code,
        "attempts": [{"number": a.number, "status": a.status, "error_code": a.error_code} for a in attempts],
        "quality_results": [{"rule_id": q.rule_id, "rule_version": q.rule_version, "outcome": q.outcome, "expected": q.expected, "observed": q.observed} for q in checks],
    }


@app.post("/api/v1/pipelines/{pipeline_id}/runs", status_code=202)
def enqueue(
    pipeline_id: str, request: RunRequest,
    key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    principal: Identity = Depends(executor), db: Session = Depends(session),
):
    pipeline = db.scalar(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.tenant_id == principal.tenant_id))
    if pipeline is None:
        raise HTTPException(404, "Pipeline not found")
    if pipeline.source_kind != "seed_orders_v1":
        raise HTTPException(422, "Pipeline kind unavailable")
    canonical = json.dumps({"pipeline_id": pipeline_id, "parameters": request.parameters}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    existing = db.scalar(select(Run).where(Run.tenant_id == principal.tenant_id, Run.idempotency_key == key))
    if existing:
        if existing.payload_digest != digest:
            raise HTTPException(409, "Idempotency key reused with different payload")
        return run_view(db, existing)
    run = Run(tenant_id=principal.tenant_id, pipeline_id=pipeline_id, idempotency_key=key, payload_digest=digest)
    db.add(run)
    db.flush()
    db.add(AuditEvent(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="pipeline.run.enqueue", target_id=run.id, outcome="QUEUED"))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = db.scalar(select(Run).where(Run.tenant_id == principal.tenant_id, Run.idempotency_key == key))
        if winner and winner.payload_digest == digest:
            return run_view(db, winner)
        raise HTTPException(409, "Idempotency key conflict") from None
    try:
        import redis
        redis.Redis.from_url(Settings.from_env().redis_url, socket_connect_timeout=0.2).publish("runs", run.id)
    except Exception:
        log.warning("Worker wakeup unavailable; database poll will recover")
    return run_view(db, run)


@app.get("/api/v1/runs/{run_id}")
def get_run(run_id: str, principal: Identity = Depends(identity), db: Session = Depends(session)):
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == principal.tenant_id))
    if run is None:
        raise HTTPException(404, "Run not found")
    return run_view(db, run)
