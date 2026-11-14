"""Bounded deterministic incident hypotheses backed by persisted evidence."""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.auth import Identity, executor, identity
from takshyra.db import session
from takshyra.models import AuditEvent, Diagnosis, Incident, IncidentEvent, QualityResult, Run, now

router = APIRouter(prefix="/api/v1/incidents/{incident_id}/diagnoses", tags=["diagnoses"])


def view(row: Diagnosis) -> dict:
    return {
        "id": row.id, "incident_id": row.incident_id, "method": row.method,
        "status": row.status, "evidence_hash": row.evidence_hash,
        "hypotheses": json.loads(row.hypotheses_json), "created_at": row.created_at,
    }


def evidence(db: Session, incident: Incident) -> tuple[dict, list[QualityResult]]:
    run = db.scalar(select(Run).where(Run.id == incident.run_id, Run.tenant_id == incident.tenant_id)) if incident.run_id else None
    checks = db.scalars(select(QualityResult).where(
        QualityResult.tenant_id == incident.tenant_id,
        QualityResult.run_id == incident.run_id,
    ).order_by(QualityResult.rule_id, QualityResult.id)).all() if run else []
    snapshot = {
        "incident_id": incident.id, "category": incident.category,
        "error_code": incident.error_code, "provenance": incident.provenance,
        "occurrences": incident.occurrence_count, "last_seen_at": incident.last_seen_at.isoformat(),
        "run": {"id": run.id, "status": run.status, "error_code": run.error_code,
                "quality_status": run.quality_status, "publication_status": run.publication_status} if run else None,
        "checks": [{"id": check.id, "rule_id": check.rule_id, "outcome": check.outcome,
                    "expected": check.expected, "observed": check.observed} for check in checks],
    }
    return snapshot, checks


def rule_hypotheses(snapshot: dict, checks: list[QualityResult]) -> list[dict]:
    incident_ref = f"incident:{snapshot['incident_id']}"
    run = snapshot["run"]
    failed = [check for check in checks if check.outcome == "FAIL"]
    row_checks = [check for check in failed if check.rule_id in {"row_count_ratio", "source_row_count_match"}]
    if row_checks:
        return [{
            "summary": "Observed row counts do not satisfy the bound data contract.",
            "category": "ROW_DEFICIT", "status": "HYPOTHESIS", "confidence_label": "MEDIUM",
            "supporting_evidence_refs": [f"check:{check.id}" for check in row_checks],
            "contradicting_evidence_refs": [],
            "unknowns": ["The upstream cause of the missing rows has not been verified."],
            "next_checks": ["Compare source and staged row counts against the contract."],
        }]
    if snapshot["error_code"] == "FRESHNESS_MISSED":
        return [{
            "summary": "The expected pipeline freshness window was missed.",
            "category": "FRESHNESS_MISS", "status": "HYPOTHESIS", "confidence_label": "LOW",
            "supporting_evidence_refs": [incident_ref], "contradicting_evidence_refs": [],
            "unknowns": ["No source or scheduler cause has been independently verified."],
            "next_checks": ["Inspect the pipeline schedule and latest upstream completion."],
        }]
    if run and run["error_code"] in {"DEMO_PERSISTENT_503", "SOURCE_UNAVAILABLE_OR_TOO_LARGE"}:
        return [{
            "summary": "The source read did not complete during the observed run.",
            "category": "SOURCE_READ_FAILURE", "status": "HYPOTHESIS", "confidence_label": "LOW",
            "supporting_evidence_refs": [f"run:{run['id']}"], "contradicting_evidence_refs": [],
            "unknowns": ["Availability, size and network causes have not been distinguished."],
            "next_checks": ["Check the source health and bounded retry history."],
        }]
    return []


@router.get("")
def list_diagnoses(incident_id: str, principal: Identity = Depends(identity), db: Session = Depends(session)):
    incident = db.scalar(select(Incident.id).where(Incident.id == incident_id, Incident.tenant_id == principal.tenant_id))
    if incident is None:
        raise HTTPException(404, "Incident not found")
    rows = db.scalars(select(Diagnosis).where(
        Diagnosis.tenant_id == principal.tenant_id, Diagnosis.incident_id == incident_id,
    ).order_by(Diagnosis.created_at.desc(), Diagnosis.id.desc()).limit(20)).all()
    return {"items": [view(row) for row in rows]}


@router.post("", status_code=201)
def create_diagnosis(incident_id: str, principal: Identity = Depends(executor), db: Session = Depends(session)):
    stmt = select(Incident).where(Incident.id == incident_id, Incident.tenant_id == principal.tenant_id)
    if db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    incident = db.scalar(stmt)
    if incident is None:
        raise HTTPException(404, "Incident not found")
    if incident.owner_id is not None and incident.owner_id != principal.user_id:
        raise HTTPException(403, "Incident is assigned to another investigator")
    snapshot, checks = evidence(db, incident)
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    existing = db.scalar(select(Diagnosis).where(
        Diagnosis.tenant_id == principal.tenant_id, Diagnosis.incident_id == incident_id,
        Diagnosis.evidence_hash == digest,
    ))
    if existing:
        return view(existing)
    hypotheses = rule_hypotheses(snapshot, checks)
    status = "HYPOTHESIS" if hypotheses else "UNKNOWN"
    diagnosis = Diagnosis(
        tenant_id=principal.tenant_id, incident_id=incident_id, evidence_hash=digest,
        method="RULES_V1", status=status,
        hypotheses_json=json.dumps(hypotheses, sort_keys=True, separators=(",", ":")),
    )
    db.add(diagnosis)
    db.flush()
    db.add(IncidentEvent(
        tenant_id=principal.tenant_id, incident_id=incident_id, kind="DIAGNOSIS",
        code=status, source_kind="INCIDENT", source_id=incident_id,
        actor_id=principal.user_id, occurred_at=now(),
    ))
    db.add(AuditEvent(
        tenant_id=principal.tenant_id, actor_id=principal.user_id,
        action="incident.diagnose", target_id=incident_id, outcome=status,
    ))
    db.commit()
    return view(diagnosis)
