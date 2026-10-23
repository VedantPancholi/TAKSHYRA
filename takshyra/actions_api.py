"""Local, tenant-scoped action proposal and execution API."""

import json
import uuid
from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.actions import (
    EXECUTION_LEASE_SECONDS, approve, apply_effect, audit, create_proposal, event,
    locked_proposal, validate_execute, verify_effect,
)
from takshyra.auth import Identity, executor, identity
from takshyra.db import session
from takshyra.models import ActionEffect, ActionEvent, ActionProposal, now

router = APIRouter(prefix="/api/v1/action-proposals")


class ProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: str = Field(min_length=1, max_length=64)
    target_id: uuid.UUID
    parameters: dict[str, str] = Field(default_factory=dict, max_length=2)


def proposal_view(db: Session, proposal: ActionProposal) -> dict:
    events = db.scalars(select(ActionEvent).where(ActionEvent.tenant_id == proposal.tenant_id,
                                                   ActionEvent.proposal_id == proposal.id)
                        .order_by(ActionEvent.occurred_at, ActionEvent.id).limit(101)).all()
    return {
        "id": proposal.id, "action_type": proposal.action_type, "target_id": proposal.target_id,
        "parameters": json.loads(proposal.parameters_json), "payload_digest": proposal.payload_digest,
        "policy_version": proposal.policy_version, "policy_decision": proposal.policy_decision,
        "policy_reason": proposal.policy_reason, "status": proposal.status,
        "requester_id": proposal.requester_id, "approver_id": proposal.approver_id,
        "expires_at": proposal.expires_at, "verification_status": proposal.verification_status,
        "effect_ref_id": proposal.effect_ref_id,
        "timeline_truncated": len(events) > 100,
        "timeline": [{"kind": row.kind, "code": row.code, "actor_id": row.actor_id,
                      "occurred_at": row.occurred_at} for row in events[:100]],
    }


@router.post("", status_code=201)
def propose_action(
    request: ProposalRequest,
    key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    principal: Identity = Depends(executor), db: Session = Depends(session),
):
    proposal = create_proposal(db, tenant_id=principal.tenant_id, requester_id=principal.user_id,
                               action_type=request.action_type, target_id=str(request.target_id),
                               parameters=request.parameters, key=key)
    return proposal_view(db, proposal)


@router.get("/{proposal_id}")
def get_proposal(proposal_id: str, principal: Identity = Depends(identity), db: Session = Depends(session)):
    proposal = locked_proposal(db, principal.tenant_id, proposal_id)
    return proposal_view(db, proposal)


@router.post("/{proposal_id}/approve")
def approve_proposal(proposal_id: str, principal: Identity = Depends(identity), db: Session = Depends(session)):
    if principal.role not in {"approver", "admin"}:
        raise HTTPException(403, "Approver role required")
    proposal = locked_proposal(db, principal.tenant_id, proposal_id)
    approve(db, proposal, principal.user_id)
    return proposal_view(db, proposal)


def finalize(db: Session, proposal: ActionProposal, actor_id: str) -> None:
    status, effect_ref = verify_effect(db, proposal)
    proposal.verification_status = status
    proposal.effect_ref_id = effect_ref
    proposal.status = status
    proposal.lease_until = None
    proposal.finished_at = now()
    event(db, proposal, "VERIFIED", status, actor_id)
    audit(db, proposal, actor_id, "action.verify", status)
    db.commit()


@router.post("/{proposal_id}/execute")
def execute_proposal(proposal_id: str, principal: Identity = Depends(executor), db: Session = Depends(session)):
    proposal = locked_proposal(db, principal.tenant_id, proposal_id)
    if proposal.requester_id != principal.user_id:
        raise HTTPException(403, "Only the requester can execute this proposal")
    if proposal.status == "VERIFIED":
        return proposal_view(db, proposal)
    if proposal.status not in {"READY", "APPROVED", "EXECUTING", "INCONCLUSIVE"}:
        raise HTTPException(409, "Proposal is not executable")
    if proposal.status == "EXECUTING" and proposal.lease_until:
        lease = proposal.lease_until
        if lease.tzinfo is None:
            lease = lease.replace(tzinfo=timezone.utc)
        if lease > now():
            raise HTTPException(409, "Execution is already leased")
    from takshyra.actions import digest_for
    if proposal.payload_digest != digest_for(proposal):
        raise HTTPException(409, "Proposal payload changed")
    existing_effect = db.get(ActionEffect, proposal.id)
    if existing_effect is None:
        validate_execute(db, proposal, principal.user_id)
    elif proposal.payload_digest != proposal.approved_digest and proposal.policy_decision == "REQUIRES_APPROVAL":
        raise HTTPException(409, "Exact payload approval required")
    if existing_effect:
        finalize(db, proposal, principal.user_id)
        return proposal_view(db, proposal)
    proposal.status = "EXECUTING"
    proposal.lease_until = now() + timedelta(seconds=EXECUTION_LEASE_SECONDS)
    event(db, proposal, "EXECUTION_CLAIMED", "LEASED", principal.user_id)
    audit(db, proposal, principal.user_id, "action.execute", "CLAIMED")
    db.commit()

    # Recheck rights and policy immediately before the bounded effect.
    with Session(db.bind) as effect_db:
        current = locked_proposal(effect_db, principal.tenant_id, proposal.id)
        validate_execute(effect_db, current, principal.user_id)
        try:
            apply_effect(effect_db, current)
        except Exception:
            effect_db.rollback()
            # A later call reconciles a committed effect before attempting another one.
            raise HTTPException(503, "Action effect unavailable; retry after lease expiry") from None

    db.expire_all()
    with Session(db.bind) as verify_db:
        current = locked_proposal(verify_db, principal.tenant_id, proposal.id)
        finalize(verify_db, current, principal.user_id)
    db.expire_all()
    return proposal_view(db, locked_proposal(db, principal.tenant_id, proposal.id))
