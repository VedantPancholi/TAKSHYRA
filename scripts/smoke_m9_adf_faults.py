"""PostgreSQL fault checks for ADF batch atomicity, replay and concurrent polls."""

import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from takshyra.adf import AdfObserver, AdfScope
from takshyra.adf_ingestion import ingest_runs, register_binding
from takshyra.db import engine
from takshyra.models import AdfPipelineBinding, AdfRunObservation, IncidentEvent, Tenant


def query(scope, runs):
    observer = AdfObserver(
        tenant_id=scope.tenant_id, allowed_targets=frozenset({scope.target}),
        transport=lambda _url, _body: {"value": runs},
    )
    until = datetime.now(timezone.utc)
    return observer.query(scope, until - timedelta(minutes=5), until)


def run(run_id, status="Failed", **fields):
    return {
        "runId": run_id, "pipelineName": "orders-adf-faults", "status": status,
        "runStart": "2026-11-15T10:00:00Z", "runEnd": "2026-11-15T10:02:00Z",
        **fields,
    }


with Session(engine()) as db:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == "demo-a"))
    scope = AdfScope(tenant.id, "00000000-0000-0000-0000-000000000001", "rg-faults", "factory-faults")
    binding = register_binding(
        db, scope=scope, local_name="orders_adf_faults", external_name="orders-adf-faults",
    )
    db.commit()
    binding_id = binding.id

    first_id, bad_id = str(uuid.uuid4()), str(uuid.uuid4())
    result = query(scope, [run(first_id), run(bad_id, runEnd="bad-timestamp")])
    event_count = db.scalar(select(func.count()).select_from(IncidentEvent).where(
        IncidentEvent.tenant_id == scope.tenant_id,
        IncidentEvent.source_kind == "ADF_RUN_OBSERVATION",
    ))
    try:
        ingest_runs(db, scope=scope, binding=binding, result=result, provenance="simulated")
        raise AssertionError("Malformed second run was accepted")
    except ValueError:
        pass
    db.commit()
    assert db.scalars(select(AdfRunObservation).where(
        AdfRunObservation.external_run_id.in_([first_id, bad_id]),
    )).all() == []
    assert db.scalar(select(func.count()).select_from(IncidentEvent).where(
        IncidentEvent.tenant_id == scope.tenant_id,
        IncidentEvent.source_kind == "ADF_RUN_OBSERVATION",
    )) == event_count

    second_id = str(uuid.uuid4())
    result = query(scope, [run(first_id), run(second_id)])
    assert ingest_runs(db, scope=scope, binding=binding, result=result,
                       provenance="simulated")["incidents"] == 2
    db.commit()
    assert ingest_runs(db, scope=scope, binding=binding, result=result,
                       provenance="simulated")["incidents"] == 0
    db.commit()
    assert db.scalar(select(func.count()).select_from(AdfRunObservation).where(
        AdfRunObservation.external_run_id.in_([first_id, second_id]),
    )) == 2
    assert db.scalar(select(func.count()).select_from(IncidentEvent).where(
        IncidentEvent.tenant_id == scope.tenant_id,
        IncidentEvent.source_kind == "ADF_RUN_OBSERVATION",
    )) == event_count + 2

concurrent_id = str(uuid.uuid4())
concurrent_result = query(scope, [run(concurrent_id)])
started, finished = threading.Event(), threading.Event()
outcome = {}


def second_poll():
    try:
        with Session(engine()) as other:
            other_binding = other.get(AdfPipelineBinding, binding_id)
            started.set()
            outcome["counts"] = ingest_runs(
                other, scope=scope, binding=other_binding,
                result=concurrent_result, provenance="simulated",
            )
            other.commit()
    except Exception as exc:
        outcome["error"] = repr(exc)
    finally:
        finished.set()


with Session(engine()) as first:
    first_binding = first.get(AdfPipelineBinding, binding_id)
    assert ingest_runs(first, scope=scope, binding=first_binding,
                       result=concurrent_result, provenance="simulated")["incidents"] == 1
    worker = threading.Thread(target=second_poll, daemon=True)
    worker.start()
    assert started.wait(5)
    time.sleep(0.25)
    assert not finished.is_set(), "Second poll passed an uncommitted first poll"
    first.commit()
    assert finished.wait(10), "Second poll did not resume after first commit"
    worker.join(timeout=1)
assert "error" not in outcome, outcome
assert outcome["counts"]["created"] == 0 and outcome["counts"]["incidents"] == 0
print("M9 ADF fault smoke passed: atomic rollback, replay and serialized PostgreSQL polls")
