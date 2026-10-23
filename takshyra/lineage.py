"""Bounded, tenant-scoped lineage ingestion and potential impact traversal."""

import hashlib
import json
from collections import deque
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from takshyra.models import Asset, AuditEvent, LineageEdge, LineageEvent, now


class DatasetRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    namespace: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)

    def key(self) -> tuple[str, str]:
        return self.namespace, self.name


class TypedRef(DatasetRef):
    type: Literal["DATASET"]


class LineageEntry(TypedRef):
    inputs: tuple[TypedRef, ...] = Field(max_length=20)


class LineageFacet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entries: tuple[LineageEntry, ...] = Field(max_length=50)


class JobFacets(BaseModel):
    model_config = ConfigDict(extra="ignore")
    lineage: LineageFacet | None = None


class JobRef(DatasetRef):
    facets: JobFacets = Field(default_factory=JobFacets)


class RunRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    runId: UUID


class RunEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eventType: Literal["COMPLETE"]
    eventTime: datetime
    producer: str = Field(min_length=1, max_length=256)
    run: RunRef
    job: JobRef
    inputs: tuple[DatasetRef, ...] = Field(default=(), max_length=20)
    outputs: tuple[DatasetRef, ...] = Field(default=(), max_length=20)

    @model_validator(mode="after")
    def validate_event(self):
        if self.eventTime.tzinfo is None:
            raise ValueError("eventTime requires timezone")
        try:
            parsed = urlsplit(self.producer)
        except ValueError as exc:
            raise ValueError("producer URL is invalid") from exc
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("producer must be an HTTPS URL without credentials or query")
        if len({item.key() for item in self.inputs}) != len(self.inputs) or len({item.key() for item in self.outputs}) != len(self.outputs):
            raise ValueError("duplicate dataset identity")
        facet = self.job.facets.lineage
        if facet is not None:
            input_keys = {item.key() for item in self.inputs}
            output_keys = {item.key() for item in self.outputs}
            if len({entry.key() for entry in facet.entries}) != len(facet.entries):
                raise ValueError("duplicate lineage target")
            for entry in facet.entries:
                if entry.key() not in output_keys or not entry.inputs:
                    raise ValueError("lineage target must be a listed output with inputs")
                if any(source.key() not in input_keys for source in entry.inputs):
                    raise ValueError("lineage source must be a listed input")
                if len({source.key() for source in entry.inputs}) != len(entry.inputs):
                    raise ValueError("duplicate lineage source")
        return self


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _upsert_asset(db: Session, tenant_id: str, ref: DatasetRef) -> Asset:
    asset = db.scalar(select(Asset).where(
        Asset.tenant_id == tenant_id, Asset.namespace == ref.namespace, Asset.name == ref.name,
    ))
    if asset is None:
        asset = Asset(tenant_id=tenant_id, namespace=ref.namespace, name=ref.name, kind="DATASET",
                      owner="unassigned", criticality="UNKNOWN", source_label="submitted metadata")
        db.add(asset)
        db.flush()
    elif asset.kind != "DATASET":
        raise HTTPException(409, "Dataset identity conflicts with another asset")
    asset.last_seen_at = now()
    return asset


def ingest(db: Session, tenant_id: str, actor_id: str, event: RunEvent) -> tuple[LineageEvent, int]:
    identity = {"producer": event.producer, "job": event.job.key(), "runId": str(event.run.runId),
                "eventType": event.eventType, "eventTime": event.eventTime.astimezone(timezone.utc).isoformat()}
    key = _digest(identity)
    payload_hash = _digest(event.model_dump(mode="json"))
    existing = db.scalar(select(LineageEvent).where(LineageEvent.tenant_id == tenant_id, LineageEvent.event_key == key))
    if existing:
        if existing.payload_hash != payload_hash:
            raise HTTPException(409, "Lineage event identity reused with different payload")
        return existing, 0
    facet = event.job.facets.lineage
    record = LineageEvent(tenant_id=tenant_id, event_key=key, payload_hash=payload_hash,
                          producer=event.producer, job_namespace=event.job.namespace, job_name=event.job.name,
                          run_id=str(event.run.runId), event_time=event.eventTime.astimezone(timezone.utc))
    count = 0
    try:
        db.add(record)
        db.flush()
        assets = {}
        for ref in (*event.inputs, *event.outputs):
            assets[ref.key()] = _upsert_asset(db, tenant_id, ref)
        if facet is not None:
            for entry in facet.entries:
                for source in entry.inputs:
                    db.add(LineageEdge(tenant_id=tenant_id, source_asset_id=assets[source.key()].id,
                                       target_asset_id=assets[entry.key()].id, relation="DERIVES_FROM",
                                       origin="observed", source_label="submitted metadata", event_id=record.id,
                                       valid_from=event.eventTime.astimezone(timezone.utc)))
                    count += 1
        db.add(AuditEvent(tenant_id=tenant_id, actor_id=actor_id, action="lineage.event.ingest",
                          target_id=record.id, outcome="ACCEPTED", safe_detail=f'{{"edge_count":{count}}}'))
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = db.scalar(select(LineageEvent).where(LineageEvent.tenant_id == tenant_id,
                                                      LineageEvent.event_key == key))
        if winner and winner.payload_hash == payload_hash:
            return winner, 0
        raise HTTPException(409, "Lineage event conflict") from None
    return record, count


def asset_view(asset: Asset) -> dict:
    return {"id": asset.id, "namespace": asset.namespace, "name": asset.name, "kind": asset.kind,
            "owner": asset.owner, "criticality": asset.criticality, "source_label": asset.source_label,
            "last_seen_at": asset.last_seen_at}


def impact(db: Session, tenant_id: str, source: Asset, *, max_depth: int, node_limit: int,
           as_of: datetime | None = None) -> dict:
    at = as_of or now()
    visited = {source.id}
    queue = deque([(source.id, [], [])])
    affected = []
    truncated = False
    while queue:
        current_id, path, edge_path = queue.popleft()
        if len(path) >= max_depth:
            if db.scalar(select(LineageEdge.id).where(
                LineageEdge.tenant_id == tenant_id, LineageEdge.source_asset_id == current_id,
                LineageEdge.valid_from <= at,
                or_(LineageEdge.valid_to.is_(None), LineageEdge.valid_to > at),
            ).limit(1)):
                truncated = True
            continue
        edges = db.scalars(select(LineageEdge).where(
            LineageEdge.tenant_id == tenant_id, LineageEdge.source_asset_id == current_id,
            LineageEdge.valid_from <= at,
            or_(LineageEdge.valid_to.is_(None), LineageEdge.valid_to > at),
        ).order_by(LineageEdge.target_asset_id, LineageEdge.id).limit(node_limit + 1)).all()
        for edge in edges:
            if edge.target_asset_id in visited:
                continue
            if len(visited) >= node_limit:
                truncated = True
                continue
            target = db.scalar(select(Asset).where(Asset.id == edge.target_asset_id, Asset.tenant_id == tenant_id))
            if target is None:
                continue
            visited.add(target.id)
            next_path = [*path, target.id]
            next_edges = [*edge_path, {"id": edge.id, "origin": edge.origin,
                                       "source_label": edge.source_label, "relation": edge.relation}]
            affected.append({**asset_view(target), "path_asset_ids": [source.id, *next_path],
                             "path_edges": next_edges, "impact_type": "potential",
                             "reasons": ["Downstream dependency in the known graph; data corruption is unverified"]})
            queue.append((target.id, next_path, next_edges))
    return {"source": asset_view(source), "as_of": at, "impact_status": "UNKNOWN" if not affected else "POTENTIAL",
            "items": affected, "truncated": truncated, "node_limit": node_limit, "max_depth": max_depth}
