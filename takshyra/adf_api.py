"""Read-only, tenant-scoped access to normalized ADF run observations."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.auth import Identity, identity
from takshyra.db import session
from takshyra.models import AdfRunObservation

router = APIRouter(prefix="/api/v1/adf-observations", tags=["azure-adf"])


@router.get("")
def list_adf_observations(principal: Identity = Depends(identity), db: Session = Depends(session)):
    rows = db.scalars(select(AdfRunObservation).where(
        AdfRunObservation.tenant_id == principal.tenant_id,
    ).order_by(AdfRunObservation.observed_at.desc(), AdfRunObservation.id.desc()).limit(50)).all()
    return {"items": [{
        "id": row.id, "pipeline_id": row.pipeline_id,
        "factory": row.factory, "external_run_id": row.external_run_id,
        "external_name": row.external_name, "status": row.status,
        "run_start": row.run_start, "run_end": row.run_end,
        "observed_at": row.observed_at, "provenance": row.provenance,
    } for row in rows]}
