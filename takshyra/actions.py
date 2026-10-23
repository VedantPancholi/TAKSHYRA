"""Server-authoritative local action policy and bounded effect registry."""

import hashlib
import html
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from takshyra.models import (
    ActionEffect, ActionEvent, ActionProposal, Attempt, AuditEvent, Incident,
    IncidentEvent, Membership, Pipeline, Run, now, uid,
)

POLICY_VERSION = "m3-v1"
ACTION_TYPES = frozenset({"incident.annotate", "notification.emit_local", "pipeline.retry_demo", "pipeline.pause_demo"})
APPROVAL_SECONDS = 600
EXECUTION_LEASE_SECONDS = 30


@dataclass(frozen=True)
class Decision:
    result: str
    reason: str
    parameters: dict[str, str]


def canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def digest_for(proposal: ActionProposal) -> str:
    payload = {
        "schema_version": 1, "tenant_id": proposal.tenant_id,
        "requester_id": proposal.requester_id, "action_type": proposal.action_type,
        "target_id": proposal.target_id, "parameters": json.loads(proposal.parameters_json),
        "policy_version": proposal.policy_version, "expires_at": canonical_time(proposal.expires_at),
    }
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


def is_expired(proposal: ActionProposal) -> bool:
    deadline = proposal.expires_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return deadline <= now()


def policy(db: Session, tenant_id: str, actor_id: str, action_type: str, target_id: str, parameters: dict[str, str]) -> Decision:
    membership = db.get(Membership, (tenant_id, actor_id))
    if membership is None or membership.role not in {"executor", "admin"}:
        return Decision("DENY", "REQUESTER_ROLE_UNAVAILABLE", {})
    if action_type not in ACTION_TYPES:
        return Decision("DENY", "ACTION_NOT_REGISTERED", {})
    if action_type == "incident.annotate":
        incident = db.scalar(select(Incident).where(Incident.id == target_id, Incident.tenant_id == tenant_id))
        if incident is None:
            return Decision("DENY", "TARGET_UNAVAILABLE", {})
        if incident.owner_id is not None and incident.owner_id != actor_id:
            return Decision("DENY", "INCIDENT_OWNER_REQUIRED", {})
        if set(parameters) != {"note"} or not 1 <= len(parameters["note"].strip()) <= 200 or any(ord(ch) < 32 for ch in parameters["note"]) or len(html.escape(parameters["note"].strip(), quote=True)) > 256:
            return Decision("DENY", "PARAMETERS_INVALID", {})
        return Decision("ALLOW", "INCIDENT_NOTE_ALLOWED", {"note": parameters["note"].strip()})
    if action_type == "notification.emit_local":
        incident = db.scalar(select(Incident).where(Incident.id == target_id, Incident.tenant_id == tenant_id))
        if incident is None:
            return Decision("DENY", "TARGET_UNAVAILABLE", {})
        if set(parameters) != {"message_code"} or parameters["message_code"] not in {"INCIDENT_OPEN", "ACTION_REQUIRED"}:
            return Decision("DENY", "PARAMETERS_INVALID", {})
        day_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
        sent = db.scalar(select(func.count()).select_from(ActionEffect).join(
            ActionProposal, ActionEffect.proposal_id == ActionProposal.id,
        ).where(ActionEffect.tenant_id == tenant_id, ActionEffect.effect_kind == action_type,
                ActionEffect.target_id == target_id, ActionEffect.created_at >= day_start))
        if sent >= 3:
            return Decision("DENY", "LOCAL_NOTIFICATION_LIMIT", {})
        return Decision("ALLOW", "LOCAL_NOTIFICATION_ALLOWED", parameters)
    if parameters:
        return Decision("DENY", "PARAMETERS_INVALID", {})
    if action_type == "pipeline.pause_demo":
        pipeline = db.scalar(select(Pipeline).where(Pipeline.id == target_id, Pipeline.tenant_id == tenant_id, Pipeline.source_kind == "seed_orders_v1"))
        return Decision("REQUIRES_APPROVAL", "SIMULATED_PAUSE_APPROVAL" , {}) if pipeline else Decision("DENY", "TARGET_UNAVAILABLE", {})
    run = db.scalar(select(Run).where(Run.id == target_id, Run.tenant_id == tenant_id))
    if run is None:
        return Decision("DENY", "TARGET_UNAVAILABLE", {})
    if run.status != "TIMED_OUT" or run.error_code != "LEASE_EXHAUSTED":
        return Decision("DENY", "NON_TRANSIENT_FAILURE", {})
    if db.scalar(select(Run).where(Run.retry_of_run_id == run.id)):
        return Decision("DENY", "RETRY_BUDGET_EXHAUSTED", {})
    if db.scalar(select(func.count()).select_from(Attempt).where(Attempt.tenant_id == tenant_id, Attempt.run_id == run.id)) < 3:
        return Decision("DENY", "RETRY_SOURCE_UNVERIFIED", {})
    return Decision("REQUIRES_APPROVAL", "BOUNDED_RETRY_APPROVAL", {})


def event(db: Session, proposal: ActionProposal, kind: str, code: str, actor_id: str | None = None) -> None:
    db.add(ActionEvent(tenant_id=proposal.tenant_id, proposal_id=proposal.id, kind=kind, code=code, actor_id=actor_id))


def audit(db: Session, proposal: ActionProposal, actor_id: str, action: str, outcome: str) -> None:
    safe_outcome = "APPROVAL_NEEDED" if outcome == "REQUIRES_APPROVAL" else outcome
    db.add(AuditEvent(tenant_id=proposal.tenant_id, actor_id=actor_id, action=action, target_id=proposal.id, outcome=safe_outcome))


def locked_proposal(db: Session, tenant_id: str, proposal_id: str) -> ActionProposal:
    stmt = select(ActionProposal).where(ActionProposal.id == proposal_id, ActionProposal.tenant_id == tenant_id)
    if db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    proposal = db.scalar(stmt)
    if proposal is None:
        raise HTTPException(404, "Action proposal not found")
    return proposal


def create_proposal(db: Session, *, tenant_id: str, requester_id: str, action_type: str, target_id: str, parameters: dict[str, str], key: str) -> ActionProposal:
    existing = db.scalar(select(ActionProposal).where(ActionProposal.tenant_id == tenant_id, ActionProposal.idempotency_key == key))
    if existing:
        normalized = policy(db, tenant_id, requester_id, action_type, target_id, parameters).parameters
        if existing.action_type == action_type and existing.target_id == target_id and json.loads(existing.parameters_json) == normalized:
            return existing
        raise HTTPException(409, "Idempotency key reused with different action")
    decision = policy(db, tenant_id, requester_id, action_type, target_id, parameters)
    expires_at = now().replace(microsecond=0) + timedelta(seconds=APPROVAL_SECONDS)
    proposal = ActionProposal(
        id=uid(),
        tenant_id=tenant_id, requester_id=requester_id, action_type=action_type, target_id=target_id,
        parameters_json=canonical_json(decision.parameters), policy_decision=decision.result,
        policy_reason=decision.reason, policy_version=POLICY_VERSION,
        status={"ALLOW": "READY", "DENY": "DENIED", "REQUIRES_APPROVAL": "AWAITING_APPROVAL"}[decision.result],
        idempotency_key=key, expires_at=expires_at,
    )
    proposal.payload_digest = digest_for(proposal)
    db.add(proposal)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        winner = db.scalar(select(ActionProposal).where(ActionProposal.tenant_id == tenant_id,
                                                        ActionProposal.idempotency_key == key))
        if winner and winner.action_type == action_type and winner.target_id == target_id and json.loads(winner.parameters_json) == policy(db, tenant_id, requester_id, action_type, target_id, parameters).parameters:
            return winner
        raise HTTPException(409, "Idempotency key conflict") from None
    event(db, proposal, "POLICY_EVALUATED", decision.result, requester_id)
    audit(db, proposal, requester_id, "action.propose", decision.result)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = db.scalar(select(ActionProposal).where(ActionProposal.tenant_id == tenant_id,
                                                        ActionProposal.idempotency_key == key))
        if winner and winner.action_type == action_type and winner.target_id == target_id and json.loads(winner.parameters_json) == policy(db, tenant_id, requester_id, action_type, target_id, parameters).parameters:
            return winner
        raise HTTPException(409, "Idempotency key conflict") from None
    return proposal


def approve(db: Session, proposal: ActionProposal, approver_id: str) -> None:
    if proposal.status != "AWAITING_APPROVAL":
        raise HTTPException(409, "Proposal is not awaiting approval")
    if proposal.requester_id == approver_id:
        raise HTTPException(403, "Self approval is not permitted")
    if is_expired(proposal):
        raise HTTPException(409, "Proposal expired")
    if proposal.payload_digest != digest_for(proposal):
        raise HTTPException(409, "Proposal payload changed")
    decision = policy(db, proposal.tenant_id, proposal.requester_id, proposal.action_type, proposal.target_id, json.loads(proposal.parameters_json))
    if decision.result != "REQUIRES_APPROVAL" or proposal.policy_version != POLICY_VERSION:
        raise HTTPException(409, "Policy or precondition changed")
    proposal.approver_id = approver_id
    proposal.approved_at = now()
    proposal.approved_digest = proposal.payload_digest
    proposal.status = "APPROVED"
    event(db, proposal, "APPROVED", "EXACT_PAYLOAD", approver_id)
    audit(db, proposal, approver_id, "action.approve", "APPROVED")
    db.commit()


def validate_execute(db: Session, proposal: ActionProposal, actor_id: str) -> None:
    if actor_id != proposal.requester_id:
        raise HTTPException(403, "Only the requester can execute this proposal")
    if is_expired(proposal):
        raise HTTPException(409, "Proposal expired")
    if proposal.payload_digest != digest_for(proposal):
        raise HTTPException(409, "Proposal payload changed")
    decision = policy(db, proposal.tenant_id, actor_id, proposal.action_type, proposal.target_id, json.loads(proposal.parameters_json))
    if decision.result != proposal.policy_decision or proposal.policy_version != POLICY_VERSION:
        raise HTTPException(409, "Policy or precondition changed")
    if decision.parameters != json.loads(proposal.parameters_json):
        raise HTTPException(409, "Validated parameters changed")
    if decision.result == "DENY":
        raise HTTPException(403, "Action denied by policy")
    if decision.result == "REQUIRES_APPROVAL":
        approver = db.get(Membership, (proposal.tenant_id, proposal.approver_id)) if proposal.approver_id else None
        if not approver or approver.role not in {"approver", "admin"} or proposal.approver_id == actor_id:
            raise HTTPException(403, "Approver role unavailable")
        if proposal.approved_digest != proposal.payload_digest or proposal.approved_at is None:
            raise HTTPException(409, "Exact payload approval required")


def apply_effect(db: Session, proposal: ActionProposal) -> str:
    existing = db.get(ActionEffect, proposal.id)
    if existing:
        return existing.target_id
    params = json.loads(proposal.parameters_json)
    target_id = proposal.target_id
    detail = ""
    if proposal.action_type == "incident.annotate":
        detail = html.escape(params["note"], quote=True)
        db.add(IncidentEvent(tenant_id=proposal.tenant_id, incident_id=target_id, kind="ANNOTATED", code="OPERATOR_NOTE", source_kind="ACTION", source_id=proposal.id, actor_id=proposal.requester_id, safe_detail=detail))
    elif proposal.action_type == "notification.emit_local":
        detail = params["message_code"]
    elif proposal.action_type == "pipeline.pause_demo":
        detail = "SIMULATED_PAUSE_ONLY"
    elif proposal.action_type == "pipeline.retry_demo":
        source = db.scalar(select(Run).where(Run.id == target_id, Run.tenant_id == proposal.tenant_id))
        retry = Run(tenant_id=proposal.tenant_id, pipeline_id=source.pipeline_id, retry_of_run_id=source.id,
                    idempotency_key=f"action-retry-{proposal.id}", payload_digest=proposal.payload_digest)
        db.add(retry)
        db.flush()
        target_id = retry.id
    else:
        raise RuntimeError("Unregistered action reached executor")
    db.add(ActionEffect(proposal_id=proposal.id, tenant_id=proposal.tenant_id, effect_kind=proposal.action_type,
                        target_id=target_id, safe_detail=detail))
    db.commit()
    return target_id


def verify_effect(db: Session, proposal: ActionProposal) -> tuple[str, str | None]:
    effect = db.get(ActionEffect, proposal.id)
    if not effect or effect.tenant_id != proposal.tenant_id or effect.effect_kind != proposal.action_type:
        return "INCONCLUSIVE", None
    if proposal.action_type == "pipeline.retry_demo":
        retry = db.scalar(select(Run).where(Run.id == effect.target_id, Run.tenant_id == proposal.tenant_id,
                                            Run.retry_of_run_id == proposal.target_id))
        return ("VERIFIED", retry.id) if retry else ("INCONCLUSIVE", None)
    if effect.target_id != proposal.target_id:
        return "INCONCLUSIVE", None
    if proposal.action_type == "incident.annotate":
        note = db.scalar(select(IncidentEvent).where(IncidentEvent.tenant_id == proposal.tenant_id,
                                                   IncidentEvent.incident_id == proposal.target_id,
                                                   IncidentEvent.source_id == proposal.id,
                                                   IncidentEvent.kind == "ANNOTATED"))
        return ("VERIFIED", effect.target_id) if note else ("INCONCLUSIVE", None)
    return "VERIFIED", effect.target_id
