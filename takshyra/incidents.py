"""Deterministic incident detection with tenant-scoped, durable observations."""

import hashlib

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from takshyra.models import Incident, IncidentEvent, now


def record_observation(
    db: Session,
    *,
    tenant_id: str,
    pipeline_id: str,
    category: str,
    severity: str,
    error_code: str,
    source_kind: str,
    source_id: str,
    provenance: str = "real observed",
    run_id: str | None = None,
    check_ids: tuple[str, ...] = (),
) -> Incident:
    """Upsert one alert; all supplied codes and references come from server-owned records."""
    at = now()
    window = at.strftime("%Y-%m-%d")  # One UTC day; recurrence on a later day opens a new incident.
    fingerprint = hashlib.sha256(f"{tenant_id}|{pipeline_id}|{category}|{error_code}|{provenance}|{window}".encode()).hexdigest()
    dialect = db.bind.dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        raise RuntimeError("Incident storage requires PostgreSQL or SQLite")
    insert = pg_insert if dialect == "postgresql" else sqlite_insert
    stmt = insert(Incident).values(
        tenant_id=tenant_id, pipeline_id=pipeline_id, run_id=run_id,
        fingerprint=fingerprint, category=category, severity=severity, provenance=provenance,
        status="OPEN", error_code=error_code, occurrence_count=1,
        first_seen_at=at, last_seen_at=at,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Incident.tenant_id, Incident.fingerprint],
        set_={
            "occurrence_count": Incident.occurrence_count + 1,
            "last_seen_at": at,
            "run_id": run_id,
        },
    ).returning(Incident.id)
    incident_id = db.scalar(stmt)
    incident = db.scalar(select(Incident).where(Incident.id == incident_id, Incident.tenant_id == tenant_id))
    db.add(IncidentEvent(
        tenant_id=tenant_id, incident_id=incident_id, kind="OBSERVED",
        code=error_code, source_kind=source_kind, source_id=source_id, occurred_at=at,
    ))
    for check_id in check_ids:
        db.add(IncidentEvent(
            tenant_id=tenant_id, incident_id=incident_id, kind="EVIDENCE",
            code="QUALITY_CHECK_FAIL", source_kind="QUALITY_RESULT", source_id=check_id,
            occurred_at=at,
        ))
    return incident
