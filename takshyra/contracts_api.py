from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.auth import Identity, identity
from takshyra.contracts import OrdersContract, canonical
from takshyra.db import session
from takshyra.models import AuditEvent, ContractVersion, Dataset

router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])


def active_orders(db: Session, tenant_id: str) -> tuple[Dataset, ContractVersion] | None:
    dataset = db.scalar(select(Dataset).where(Dataset.tenant_id == tenant_id, Dataset.ref == "demo.orders_curated"))
    if dataset is None:
        return None
    version = db.scalar(select(ContractVersion).where(
        ContractVersion.tenant_id == tenant_id, ContractVersion.dataset_id == dataset.id,
        ContractVersion.version == dataset.active_version,
    ))
    return (dataset, version) if version else None


def view(dataset: Dataset, version: ContractVersion) -> dict:
    return {"dataset_id": dataset.id, "dataset_ref": dataset.ref, "owner": dataset.owner,
            "version": version.version, "definition_hash": version.definition_hash,
            "definition": OrdersContract.model_validate_json(version.definition_json).model_dump(mode="json"),
            "active": version.version == dataset.active_version}


@router.get("")
def list_contracts(principal: Identity = Depends(identity), db: Session = Depends(session)):
    pair = active_orders(db, principal.tenant_id)
    return {"items": [view(*pair)] if pair else []}


@router.get("/{dataset_id}/versions/{version_number}")
def get_contract(dataset_id: str, version_number: int, principal: Identity = Depends(identity),
                 db: Session = Depends(session)):
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.tenant_id == principal.tenant_id))
    if dataset is None:
        raise HTTPException(404, "Dataset not found")
    version = db.scalar(select(ContractVersion).where(
        ContractVersion.dataset_id == dataset.id, ContractVersion.tenant_id == principal.tenant_id,
        ContractVersion.version == version_number,
    ))
    if version is None:
        raise HTTPException(404, "Contract version not found")
    return view(dataset, version)


@router.post("/{dataset_id}/versions", status_code=201)
def create_version(dataset_id: str, definition: OrdersContract, principal: Identity = Depends(identity),
                   db: Session = Depends(session)):
    if principal.role not in {"approver", "admin"}:
        raise HTTPException(403, "Contract management permission required")
    stmt = select(Dataset).where(Dataset.id == dataset_id, Dataset.tenant_id == principal.tenant_id)
    if db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    dataset = db.scalar(stmt)
    if dataset is None:
        raise HTTPException(404, "Dataset not found")
    serialized, digest = canonical(definition)
    active = db.scalar(select(ContractVersion).where(
        ContractVersion.dataset_id == dataset.id, ContractVersion.version == dataset.active_version,
    ))
    if active and active.definition_hash == digest:
        raise HTTPException(409, "Definition already active")
    next_version = dataset.active_version + 1
    version = ContractVersion(tenant_id=principal.tenant_id, dataset_id=dataset.id, version=next_version,
                              definition_json=serialized, definition_hash=digest)
    db.add(version)
    dataset.active_version = next_version
    db.add(AuditEvent(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="contract.version.create",
                      target_id=dataset.id, outcome="CREATED", safe_detail=f'{{"version":{next_version}}}'))
    db.commit()
    return view(dataset, version)
