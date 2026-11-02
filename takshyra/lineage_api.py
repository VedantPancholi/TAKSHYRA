from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.auth import Identity, executor, identity
from takshyra.db import session
from takshyra.lineage import RunEvent, asset_view, impact, ingest
from takshyra.models import Asset, Incident, Pipeline

router = APIRouter(prefix="/api/v1", tags=["lineage"])


@router.get("/assets")
def list_assets(principal: Identity = Depends(identity), db: Session = Depends(session)):
    rows = db.scalars(select(Asset).where(Asset.tenant_id == principal.tenant_id)
                      .order_by(Asset.namespace, Asset.name).limit(100)).all()
    return {"items": [asset_view(row) for row in rows]}


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, principal: Identity = Depends(identity), db: Session = Depends(session)):
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.tenant_id == principal.tenant_id))
    if asset is None:
        raise HTTPException(404, "Asset not found")
    return asset_view(asset)


@router.post("/lineage/events", status_code=201)
async def ingest_event(event: RunEvent, request: Request, principal: Identity = Depends(executor),
                       db: Session = Depends(session)):
    if len(await request.body()) > 64_000:
        raise HTTPException(413, "Lineage event too large")
    record, count = ingest(db, principal.tenant_id, principal.user_id, event)
    return {"id": record.id, "edge_count": count, "event_time": record.event_time,
            "source_label": "submitted metadata"}


def _bounds(as_of: datetime | None):
    if as_of is not None and as_of.tzinfo is None:
        raise HTTPException(422, "as_of requires timezone")
    return as_of.astimezone(timezone.utc) if as_of else None


@router.get("/lineage/{asset_id}/impact")
def asset_impact(asset_id: str, max_depth: int = Query(default=4, ge=1, le=8),
                 node_limit: int = Query(default=100, ge=2, le=500), as_of: datetime | None = None,
                 principal: Identity = Depends(identity), db: Session = Depends(session)):
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.tenant_id == principal.tenant_id))
    if asset is None:
        raise HTTPException(404, "Asset not found")
    return impact(db, principal.tenant_id, asset, max_depth=max_depth, node_limit=node_limit,
                  as_of=_bounds(as_of))


@router.get("/incidents/{incident_id}/impact")
def incident_impact(incident_id: str, max_depth: int = Query(default=4, ge=1, le=8),
                    node_limit: int = Query(default=100, ge=2, le=500),
                    principal: Identity = Depends(identity), db: Session = Depends(session)):
    incident = db.scalar(select(Incident).where(Incident.id == incident_id,
                                                Incident.tenant_id == principal.tenant_id))
    if incident is None:
        raise HTTPException(404, "Incident not found")
    pipeline = db.scalar(select(Pipeline).where(Pipeline.id == incident.pipeline_id,
                                                Pipeline.tenant_id == principal.tenant_id))
    asset = db.scalar(select(Asset).where(Asset.id == pipeline.output_asset_id,
                                           Asset.tenant_id == principal.tenant_id)) if pipeline and pipeline.output_asset_id else None
    if asset is None:
        return {"incident_id": incident.id, "impact_status": "UNKNOWN", "source": None,
                "items": [], "truncated": False, "reasons": ["No output asset mapping is available"]}
    result = impact(db, principal.tenant_id, asset, max_depth=max_depth, node_limit=node_limit,
                    as_of=incident.last_seen_at)
    result["incident_id"] = incident.id
    result["incident_provenance"] = incident.provenance
    return result
