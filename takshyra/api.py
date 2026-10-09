import hashlib
import json
import logging
import uuid
from typing import Literal

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from takshyra.auth import Identity, executor, identity
from takshyra.config import Settings
from takshyra.db import session
from takshyra.incidents import record_observation
from takshyra.models import Attempt, AuditEvent, Incident, IncidentEvent, Pipeline, QualityResult, Run, now

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
    demo_fault: Literal["F02", "F03", "F04"] | None = None


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["INVESTIGATING"]


class EmptyDemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


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
        "demo_fault": run.demo_fault, "next_attempt_at": run.next_attempt_at,
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
    canonical = json.dumps({"pipeline_id": pipeline_id, "parameters": request.parameters, "demo_fault": request.demo_fault}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    existing = db.scalar(select(Run).where(Run.tenant_id == principal.tenant_id, Run.idempotency_key == key))
    if existing:
        if existing.payload_digest != digest:
            raise HTTPException(409, "Idempotency key reused with different payload")
        return run_view(db, existing)
    run = Run(tenant_id=principal.tenant_id, pipeline_id=pipeline_id, idempotency_key=key, payload_digest=digest, demo_fault=request.demo_fault)
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


def incident_view(db: Session, incident: Incident, *, timeline: bool = False) -> dict:
    result = {
        "id": incident.id, "pipeline_id": incident.pipeline_id, "run_id": incident.run_id,
        "owner_id": incident.owner_id,
        "category": incident.category, "severity": incident.severity,
        "status": incident.status, "error_code": incident.error_code,
        "occurrence_count": incident.occurrence_count,
        "first_seen_at": incident.first_seen_at, "last_seen_at": incident.last_seen_at,
        "diagnosis_status": "UNKNOWN",
        "provenance": incident.provenance,
    }
    if timeline:
        events = db.scalars(
            select(IncidentEvent).where(
                IncidentEvent.tenant_id == incident.tenant_id,
                IncidentEvent.incident_id == incident.id,
            ).order_by(IncidentEvent.occurred_at, IncidentEvent.id).limit(101)
        ).all()
        result["timeline_truncated"] = len(events) > 100
        result["timeline"] = [
            {"kind": event.kind, "code": event.code, "source_kind": event.source_kind,
             "source_id": event.source_id, "occurred_at": event.occurred_at}
            for event in events[:100]
        ]
    return result


@app.get("/api/v1/incidents")
def list_incidents(principal: Identity = Depends(identity), db: Session = Depends(session)):
    incidents = db.scalars(
        select(Incident).where(Incident.tenant_id == principal.tenant_id)
        .order_by(Incident.last_seen_at.desc(), Incident.id).limit(100)
    ).all()
    return {"items": [incident_view(db, incident) for incident in incidents]}


@app.get("/api/v1/incidents/{incident_id}")
def get_incident(incident_id: str, principal: Identity = Depends(identity), db: Session = Depends(session)):
    incident = db.scalar(select(Incident).where(Incident.id == incident_id, Incident.tenant_id == principal.tenant_id))
    if incident is None:
        raise HTTPException(404, "Incident not found")
    return incident_view(db, incident, timeline=True)


@app.patch("/api/v1/incidents/{incident_id}")
def investigate_incident(
    incident_id: str, request: IncidentUpdate,
    principal: Identity = Depends(executor), db: Session = Depends(session),
):
    stmt = select(Incident).where(Incident.id == incident_id, Incident.tenant_id == principal.tenant_id)
    if db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    incident = db.scalar(stmt)
    if incident is None:
        raise HTTPException(404, "Incident not found")
    if incident.owner_id is not None and incident.owner_id != principal.user_id:
        raise HTTPException(403, "Incident is assigned to another investigator")
    if incident.status == "OPEN":
        incident.status = request.status
        incident.owner_id = principal.user_id
        db.add(IncidentEvent(
            tenant_id=principal.tenant_id, incident_id=incident.id, kind="STATUS_CHANGED",
            code="INVESTIGATING", source_kind="INCIDENT", source_id=incident.id,
            actor_id=principal.user_id, occurred_at=now(),
        ))
        db.add(AuditEvent(
            tenant_id=principal.tenant_id, actor_id=principal.user_id,
            action="incident.investigate", target_id=incident.id, outcome="INVESTIGATING",
        ))
        db.commit()
    return incident_view(db, incident, timeline=True)


@app.post("/api/v1/demo/pipelines/{pipeline_id}/freshness-miss", status_code=201)
def demo_freshness_miss(
    pipeline_id: str, request: EmptyDemoRequest = Body(default=EmptyDemoRequest()),
    principal: Identity = Depends(executor), db: Session = Depends(session),
):
    if Settings.from_env().app_env != "development":
        raise HTTPException(403, "Demo faults unavailable")
    pipeline = db.scalar(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.tenant_id == principal.tenant_id))
    if pipeline is None:
        raise HTTPException(404, "Pipeline not found")
    incident = record_observation(
        db, tenant_id=principal.tenant_id, pipeline_id=pipeline.id,
        category="FRESHNESS_FAILURE", severity="MEDIUM", provenance="simulated", error_code="FRESHNESS_MISSED",
        source_kind="PIPELINE", source_id=pipeline.id,
    )
    db.add(AuditEvent(
        tenant_id=principal.tenant_id, actor_id=principal.user_id,
        action="demo.freshness_miss", target_id=incident.id, outcome="RECORDED",
    ))
    db.commit()
    return incident_view(db, incident, timeline=True)
