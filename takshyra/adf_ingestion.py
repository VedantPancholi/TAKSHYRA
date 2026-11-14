"""Persist allowlisted ADF run metadata and create evidence for failed runs."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.adf import AdfScope, STATUS
from takshyra.incidents import record_observation
from takshyra.models import AdfPipelineBinding, AdfRunObservation, Pipeline, now

FAILURES = {"Failed": ("ADF_RUN_FAILED", "HIGH"), "Cancelled": ("ADF_RUN_CANCELLED", "MEDIUM")}
TERMINAL = {"Succeeded", "Failed", "Cancelled"}


def register_binding(
    db: Session, *, scope: AdfScope, local_name: str, external_name: str,
) -> AdfPipelineBinding:
    """Explicitly bind one tenant-owned local pipeline to one ADF pipeline."""
    if not 1 <= len(local_name) <= 64 or not 1 <= len(external_name) <= 128:
        raise ValueError("Pipeline names exceed local limits")
    existing_target = db.scalar(select(AdfPipelineBinding).where(
        AdfPipelineBinding.tenant_id == scope.tenant_id,
        AdfPipelineBinding.factory == scope.target,
        AdfPipelineBinding.external_name == external_name,
    ))
    pipeline = db.scalar(select(Pipeline).where(
        Pipeline.tenant_id == scope.tenant_id, Pipeline.name == local_name,
    ))
    if pipeline is None:
        if existing_target is not None:
            raise ValueError("ADF target is already bound to another local pipeline")
        pipeline = Pipeline(tenant_id=scope.tenant_id, name=local_name, source_kind="azure_adf_v1")
        db.add(pipeline)
        db.flush()
    elif pipeline.source_kind != "azure_adf_v1":
        raise ValueError("Local pipeline belongs to a different source")
    binding = db.scalar(select(AdfPipelineBinding).where(
        AdfPipelineBinding.tenant_id == scope.tenant_id,
        AdfPipelineBinding.pipeline_id == pipeline.id,
    ))
    if binding is not None:
        if binding.factory != scope.target or binding.external_name != external_name:
            raise ValueError("Local pipeline is already bound to another ADF target")
        return binding
    if existing_target is not None:
        raise ValueError("ADF target is already bound to another local pipeline")
    binding = AdfPipelineBinding(
        tenant_id=scope.tenant_id, pipeline_id=pipeline.id,
        factory=scope.target, external_name=external_name,
    )
    db.add(binding)
    db.flush()
    return binding


def _timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("Invalid ADF timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid ADF timestamp") from None
    if parsed.tzinfo is None:
        raise ValueError("ADF timestamp must include a timezone")
    return parsed


def ingest_runs(
    db: Session, *, scope: AdfScope, binding: AdfPipelineBinding, result: dict,
    provenance: str = "real observed",
) -> dict[str, int]:
    """Ingest a complete, normalized observer result. Caller owns the transaction."""
    if (binding.tenant_id != scope.tenant_id or binding.factory != scope.target or
            not db.scalar(select(Pipeline.id).where(
                Pipeline.tenant_id == scope.tenant_id,
                Pipeline.id == binding.pipeline_id,
                Pipeline.source_kind == "azure_adf_v1",
            ))):
        raise PermissionError("ADF binding does not match tenant and pipeline")
    if (not isinstance(result, dict) or result.get("truncated") is not False or
            not isinstance(result.get("items"), list) or len(result["items"]) > 100):
        raise ValueError("A complete ADF observer result is required")
    if provenance not in {"real observed", "simulated"}:
        raise ValueError("Unsupported ADF provenance")
    counts = {"created": 0, "updated": 0, "incidents": 0, "skipped": 0}
    seen: set[str] = set()
    for item in result["items"]:
        if not isinstance(item, dict) or item.get("source") != "azure_adf":
            raise ValueError("Invalid ADF observation")
        if item.get("tenant_id") != scope.tenant_id or item.get("factory") != scope.target:
            raise PermissionError("ADF observation outside tenant allowlist")
        if item.get("pipeline_name") != binding.external_name:
            counts["skipped"] += 1
            continue
        run_id = item.get("run_id")
        status = item.get("status")
        if not isinstance(run_id, str) or not 1 <= len(run_id) <= 128 or status not in STATUS:
            raise ValueError("Invalid ADF run fields")
        if run_id in seen:
            raise ValueError("Duplicate ADF run in one response")
        seen.add(run_id)
        start, end = _timestamp(item.get("run_start")), _timestamp(item.get("run_end"))
        if start is not None and end is not None and end < start:
            raise ValueError("ADF run end precedes start")
        row = db.scalar(select(AdfRunObservation).where(
            AdfRunObservation.tenant_id == scope.tenant_id,
            AdfRunObservation.factory == scope.target,
            AdfRunObservation.external_run_id == run_id,
        ))
        if row is None:
            row = AdfRunObservation(
                tenant_id=scope.tenant_id, pipeline_id=binding.pipeline_id,
                factory=scope.target, external_run_id=run_id,
                external_name=binding.external_name, status=status, provenance=provenance,
                run_start=start, run_end=end, failure_reported=False,
            )
            db.add(row)
            db.flush()
            counts["created"] += 1
        else:
            if (row.pipeline_id != binding.pipeline_id or row.external_name != binding.external_name or
                    row.provenance != provenance):
                raise ValueError("ADF run already belongs to another binding")
            if row.status in TERMINAL and row.status != status:
                raise ValueError("ADF terminal run status changed")
            row.status, row.run_start, row.run_end, row.observed_at = status, start, end, now()
            counts["updated"] += 1
        if status in FAILURES and not row.failure_reported:
            code, severity = FAILURES[status]
            record_observation(
                db, tenant_id=scope.tenant_id, pipeline_id=binding.pipeline_id,
                category="EXECUTION_FAILURE", severity=severity, error_code=code,
                provenance=provenance, source_kind="ADF_RUN_OBSERVATION", source_id=row.id,
            )
            row.failure_reported = True
            counts["incidents"] += 1
    return counts
