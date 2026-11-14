"""Local shadow replay and independent post-action recovery checks."""

import hashlib
import json
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.auth import Identity, executor, identity
from takshyra.config import Settings
from takshyra.contracts import OrdersContract, canonical
from takshyra.db import session
from takshyra.models import (
    ActionEffect, ActionProposal, AuditEvent, ContractVersion, Incident, IncidentEvent,
    QualityResult, RecoveryOutcome, Run, ShadowReplay,
)
from takshyra.runner import read_manifest, transform

router = APIRouter(tags=["recovery"])


def replay_view(row: ShadowReplay) -> dict:
    return {
        "id": row.id, "incident_id": row.incident_id, "source_run_id": row.source_run_id,
        "status": row.status, "reason": row.reason, "source_sha256": row.source_sha256,
        "contract_hash": row.contract_hash, "baseline_row_count": row.baseline_row_count,
        "replay_row_count": row.replay_row_count, "replay_sha256": row.replay_sha256,
        "created_at": row.created_at,
    }


def outcome_view(row: RecoveryOutcome) -> dict:
    return {
        "id": row.id, "incident_id": row.incident_id, "proposal_id": row.proposal_id,
        "recovery_run_id": row.recovery_run_id, "status": row.status,
        "reason": row.reason, "manifest_sha256": row.manifest_sha256,
        "verified_by": row.verified_by, "created_at": row.created_at,
    }


def source_digest(settings: Settings) -> str:
    source = Path(settings.fixture_path).resolve()
    if not source.is_file() or source.stat().st_size > 10_000_000:
        raise ValueError("SOURCE_UNAVAILABLE_OR_TOO_LARGE")
    return hashlib.sha256(source.read_bytes()).hexdigest()


def incident_for(db: Session, tenant_id: str, incident_id: str) -> Incident:
    incident = db.scalar(select(Incident).where(
        Incident.id == incident_id, Incident.tenant_id == tenant_id,
    ))
    if incident is None:
        raise HTTPException(404, "Incident not found")
    return incident


@router.get("/api/v1/incidents/{incident_id}/shadow-replays")
def list_replays(incident_id: str, principal: Identity = Depends(identity), db: Session = Depends(session)):
    incident_for(db, principal.tenant_id, incident_id)
    rows = db.scalars(select(ShadowReplay).where(
        ShadowReplay.tenant_id == principal.tenant_id, ShadowReplay.incident_id == incident_id,
    ).order_by(ShadowReplay.created_at.desc(), ShadowReplay.id.desc()).limit(20)).all()
    return {"items": [replay_view(row) for row in rows]}


@router.post("/api/v1/incidents/{incident_id}/shadow-replays", status_code=201)
def create_replay(incident_id: str, principal: Identity = Depends(executor), db: Session = Depends(session)):
    incident = incident_for(db, principal.tenant_id, incident_id)
    if incident.owner_id is not None and incident.owner_id != principal.user_id:
        raise HTTPException(403, "Incident is assigned to another investigator")
    if incident.status == "RESOLVED" or not incident.run_id:
        raise HTTPException(409, "Incident has no active source run")
    source = db.scalar(select(Run).where(
        Run.id == incident.run_id, Run.tenant_id == principal.tenant_id,
        Run.pipeline_id == incident.pipeline_id,
    ))
    if source is None or source.status not in {"SUCCEEDED", "FAILED", "TIMED_OUT"}:
        raise HTTPException(409, "Source run is not finished")
    version = db.scalar(select(ContractVersion).where(
        ContractVersion.id == source.contract_version_id,
        ContractVersion.tenant_id == principal.tenant_id,
    )) if source.contract_version_id else None
    if version is None:
        raise HTTPException(409, "Bound contract unavailable")
    try:
        contract = OrdersContract.model_validate_json(version.definition_json)
        contract_hash = canonical(contract)[1]
        input_hash = source_digest(Settings.from_env())
    except (ValueError, OSError):
        raise HTTPException(409, "Replay input unavailable") from None
    if contract_hash != version.definition_hash:
        raise HTTPException(409, "Bound contract changed")
    prior = db.scalar(select(ShadowReplay).where(
        ShadowReplay.tenant_id == principal.tenant_id,
        ShadowReplay.incident_id == incident_id,
        ShadowReplay.source_run_id == source.id,
        ShadowReplay.source_sha256 == input_hash,
        ShadowReplay.contract_hash == contract_hash,
    ).order_by(ShadowReplay.created_at.desc()).limit(1))
    if prior:
        return replay_view(prior)
    settings = Settings.from_env()
    baseline = read_manifest(settings.output_dir, principal.tenant_id, source.id)
    status, reason = "PARTIAL", "SOURCE_RESULT_UNAVAILABLE"
    replay = None
    if incident.category == "QUALITY_FAILURE" and source.demo_fault == "F04" and baseline:
        try:
            Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="shadow-", dir=settings.output_dir) as scratch:
                snapshot = Path(scratch) / "source.csv"
                shutil.copyfile(settings.fixture_path, snapshot)
                if hashlib.sha256(snapshot.read_bytes()).hexdigest() != input_hash:
                    raise ValueError("SHADOW_INPUT_CHANGED")
                replay = transform(str(snapshot), scratch, principal.tenant_id, str(uuid.uuid4()),
                                   contract=contract, contract_version=version.version)
        except (ValueError, OSError):
            replay = None
            status, reason = "PARTIAL", "SHADOW_TRANSFORM_UNAVAILABLE"
        if (replay and source.quality_status == "FAIL" and baseline.get("quality_status") == "FAIL"
                and replay["quality_status"] == "PASS" and replay["publication_status"] == "PUBLISHED"
                and replay["row_count"] > baseline["row_count"]):
            status, reason = "SUPPORTED", "LOCAL_ROW_DEFICIT_REPAIRED_IN_SHADOW"
        elif replay:
            status, reason = "PARTIAL", "INVARIANT_NOT_RESTORED_IN_SHADOW"
    elif incident.category != "QUALITY_FAILURE" or source.demo_fault != "F04":
        status, reason = "IMPOSSIBLE", "UNSUPPORTED_LOCAL_FAILURE"
    row = ShadowReplay(
        tenant_id=principal.tenant_id, incident_id=incident.id, source_run_id=source.id,
        source_sha256=input_hash, contract_hash=contract_hash, status=status, reason=reason,
        baseline_row_count=baseline.get("row_count") if baseline else None,
        replay_row_count=replay.get("row_count") if replay else None,
        replay_sha256=replay.get("sha256") if replay else None,
    )
    db.add(row)
    db.flush()
    db.add(IncidentEvent(tenant_id=principal.tenant_id, incident_id=incident.id,
                         kind="SHADOW_REPLAY", code=status, source_kind="SHADOW_REPLAY", source_id=row.id,
                         actor_id=principal.user_id))
    db.add(AuditEvent(tenant_id=principal.tenant_id, actor_id=principal.user_id,
                      action="recovery.shadow_replay", target_id=row.id, outcome=status))
    db.commit()
    return replay_view(row)


def proposal_context(db: Session, tenant_id: str, proposal_id: str, *, lock: bool = False) -> tuple[ActionProposal, ShadowReplay, Incident, Run | None]:
    statement = select(ActionProposal).where(
        ActionProposal.id == proposal_id, ActionProposal.tenant_id == tenant_id,
        ActionProposal.action_type == "pipeline.reprocess_demo",
    )
    if lock and db.bind.dialect.name == "postgresql":
        statement = statement.with_for_update()
    proposal = db.scalar(statement)
    if proposal is None:
        raise HTTPException(404, "Recovery proposal not found")
    report_id = json.loads(proposal.parameters_json).get("shadow_report_id")
    report = db.scalar(select(ShadowReplay).where(
        ShadowReplay.id == report_id, ShadowReplay.tenant_id == tenant_id,
        ShadowReplay.source_run_id == proposal.target_id,
    ))
    if report is None:
        raise HTTPException(409, "Shadow report unavailable")
    incident = incident_for(db, tenant_id, report.incident_id)
    effect = db.scalar(select(ActionEffect).where(
        ActionEffect.proposal_id == proposal.id, ActionEffect.tenant_id == tenant_id,
        ActionEffect.effect_kind == proposal.action_type,
    ))
    run = db.scalar(select(Run).where(
        Run.id == effect.target_id, Run.tenant_id == tenant_id,
        Run.retry_of_run_id == proposal.target_id,
    )) if effect else None
    return proposal, report, incident, run


@router.get("/api/v1/action-proposals/{proposal_id}/recovery-outcome")
def get_outcome(proposal_id: str, principal: Identity = Depends(identity), db: Session = Depends(session)):
    proposal_context(db, principal.tenant_id, proposal_id)
    outcome = db.scalar(select(RecoveryOutcome).where(
        RecoveryOutcome.tenant_id == principal.tenant_id, RecoveryOutcome.proposal_id == proposal_id,
    ))
    return outcome_view(outcome) if outcome else {"status": "NOT_VERIFIED"}


@router.post("/api/v1/action-proposals/{proposal_id}/verify-recovery")
def verify_recovery(proposal_id: str, principal: Identity = Depends(executor), db: Session = Depends(session)):
    proposal, report, incident, run = proposal_context(db, principal.tenant_id, proposal_id, lock=True)
    if proposal.requester_id != principal.user_id:
        raise HTTPException(403, "Only the requester can start recovery verification")
    existing = db.scalar(select(RecoveryOutcome).where(
        RecoveryOutcome.tenant_id == principal.tenant_id, RecoveryOutcome.proposal_id == proposal_id,
    ))
    if existing:
        return outcome_view(existing)
    if run is None or proposal.status != "VERIFIED":
        raise HTTPException(409, "Recovery action has not enqueued a run")
    if run.status in {"QUEUED", "RUNNING"}:
        return {"status": "INCONCLUSIVE", "reason": "RECOVERY_RUN_PENDING", "recovery_run_id": run.id}
    settings = Settings.from_env()
    manifest = read_manifest(settings.output_dir, principal.tenant_id, run.id)
    checks = db.scalars(select(QualityResult).where(
        QualityResult.tenant_id == principal.tenant_id, QualityResult.run_id == run.id,
    )).all()
    try:
        source_unchanged = source_digest(settings) == report.source_sha256
    except (ValueError, OSError):
        source_unchanged = False
    valid = (
        report.status == "SUPPORTED" and incident.run_id == report.source_run_id
        and source_unchanged and run.contract_version_id is not None
        and run.status == "SUCCEEDED" and run.quality_status == "PASS"
        and run.publication_status == "PUBLISHED" and manifest is not None
        and manifest.get("contract_hash") == report.contract_hash
        and manifest.get("row_count") == report.replay_row_count
        and manifest.get("quality_status") == "PASS"
        and manifest.get("publication_status") == "PUBLISHED"
        and bool(checks) and all(check.outcome == "PASS" for check in checks)
    )
    status = "VERIFIED" if valid else "FAILED"
    reason = "SOURCE_AND_CONTRACT_INVARIANTS_RESTORED" if valid else "RECOVERY_INVARIANTS_NOT_MET"
    outcome = RecoveryOutcome(
        tenant_id=principal.tenant_id, incident_id=incident.id, proposal_id=proposal.id,
        recovery_run_id=run.id, status=status, reason=reason,
        manifest_sha256=manifest.get("sha256") if manifest else None,
        verified_by=principal.user_id,
    )
    db.add(outcome)
    db.flush()
    if valid:
        incident.status = "RESOLVED"
        db.add(IncidentEvent(tenant_id=principal.tenant_id, incident_id=incident.id,
                             kind="RECOVERY_VERIFIED", code=status, source_kind="RECOVERY_OUTCOME",
                             source_id=outcome.id, actor_id=principal.user_id))
    db.add(AuditEvent(tenant_id=principal.tenant_id, actor_id=principal.user_id,
                      action="recovery.verify", target_id=outcome.id, outcome=status))
    db.commit()
    return outcome_view(outcome)
