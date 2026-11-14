"""Tenant-scoped local stream lab endpoints."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.auth import Identity, executor, identity
from takshyra.config import Settings
from takshyra.db import session
from takshyra.incidents import record_observation
from takshyra.models import AuditEvent, Pipeline, StreamObservation
from takshyra.streaming import evaluate

router = APIRouter(prefix="/api/v1/stream-observations", tags=["streaming"])


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["CLEAN", "SCHEMA_V15", "SINK_GAP", "CONSUMER_LAG", "DUPLICATE", "LATE_EVENT"]


def view(row: StreamObservation, incident_id: str | None = None) -> dict:
    return {
        "id": row.id, "pipeline_id": row.pipeline_id, "scenario": row.scenario,
        "status": row.status, "error_code": row.error_code,
        "metrics": json.loads(row.metrics_json), "incident_id": incident_id,
        "created_at": row.created_at, "provenance": "simulated",
    }


@router.get("")
def list_observations(principal: Identity = Depends(identity), db: Session = Depends(session)):
    rows = db.scalars(select(StreamObservation).where(
        StreamObservation.tenant_id == principal.tenant_id,
    ).order_by(StreamObservation.created_at.desc(), StreamObservation.id.desc()).limit(50)).all()
    return {"items": [view(row) for row in rows]}


@router.post("/demo", status_code=201)
def run_scenario(request: ScenarioRequest, principal: Identity = Depends(executor), db: Session = Depends(session)):
    if Settings.from_env().app_env != "development":
        raise HTTPException(403, "Demo scenarios unavailable")
    pipeline = db.scalar(select(Pipeline).where(
        Pipeline.tenant_id == principal.tenant_id, Pipeline.source_kind == "telemetry_demo_v1",
    ))
    if pipeline is None:
        raise HTTPException(503, "Telemetry demo pipeline unavailable")
    status, code, metrics = evaluate(request.scenario)
    row = StreamObservation(
        tenant_id=principal.tenant_id, pipeline_id=pipeline.id,
        scenario=request.scenario, status=status, error_code=code,
        metrics_json=json.dumps(metrics, sort_keys=True),
    )
    db.add(row)
    db.flush()
    incident = record_observation(
        db, tenant_id=principal.tenant_id, pipeline_id=pipeline.id,
        category="QUALITY_FAILURE", severity="HIGH" if request.scenario in {"SCHEMA_V15", "SINK_GAP"} else "MEDIUM",
        provenance="simulated", error_code=code,
        source_kind="STREAM_OBSERVATION", source_id=row.id,
    ) if code else None
    db.add(AuditEvent(
        tenant_id=principal.tenant_id, actor_id=principal.user_id,
        action="demo.stream.observe", target_id=row.id, outcome=status,
    ))
    db.commit()
    return view(row, incident.id if incident else None)
