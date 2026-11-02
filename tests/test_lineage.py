from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.api import app
from takshyra.models import Asset, LineageEdge, LineageEvent, now
from takshyra.worker import process_one
from test_foundation import auth, local as m5_setup, pipeline_id  # noqa: F401


def test_seeded_graph_and_incident_impact(request):
    settings, engine = request.getfixturevalue("m5_setup")
    client = TestClient(app)
    headers, credentials = auth()
    viewer_headers, viewer_credentials = auth("demo-a-viewer")
    other_headers, other_credentials = auth("demo-b-executor", "demo-b")
    assets = client.get("/api/v1/assets", headers=headers, auth=credentials).json()["items"]
    assert len(assets) == 7
    by_name = {asset["name"]: asset for asset in assets}
    curated = by_name["demo.orders_curated"]
    impact_route = f"/api/v1/lineage/{curated['id']}/impact"
    result = client.get(impact_route, headers=viewer_headers, auth=viewer_credentials).json()
    assert result["impact_status"] == "POTENTIAL" and result["truncated"] is False
    assert {asset["name"] for asset in result["items"]} == {"demo.revenue_dashboard", "demo.sales_forecast"}
    assert all(asset["impact_type"] == "potential" for asset in result["items"])
    assert all(asset["path_edges"][0]["source_label"] == "simulated" for asset in result["items"])
    assert client.get(impact_route, headers=other_headers, auth=other_credentials).status_code == 404
    assert client.get(f"/api/v1/assets/{curated['id']}", headers=other_headers, auth=other_credentials).status_code == 404
    assert client.get(impact_route, headers=headers, auth=credentials, params={"node_limit": 1}).status_code == 422
    limited = client.get(impact_route, headers=headers, auth=credentials, params={"node_limit": 2}).json()
    assert len(limited["items"]) == 1 and limited["truncated"] is True
    raw = by_name["demo.orders_raw"]
    shallow = client.get(f"/api/v1/lineage/{raw['id']}/impact", headers=headers,
                         auth=credentials, params={"max_depth": 1}).json()
    assert [item["name"] for item in shallow["items"]] == ["demo.orders_curated"]
    assert shallow["truncated"] is True

    with Session(engine) as db:
        tenant_id = db.get(Asset, curated["id"]).tenant_id
        db.add(LineageEdge(tenant_id=tenant_id, source_asset_id=by_name["demo.revenue_dashboard"]["id"],
                           target_asset_id=curated["id"], relation="SERVES", origin="declared",
                           source_label="simulated", valid_from=now()))
        db.add(LineageEdge(tenant_id=tenant_id, source_asset_id=curated["id"],
                           target_asset_id=by_name["demo.operations_dashboard"]["id"], relation="SERVES",
                           origin="declared", source_label="simulated", valid_from=now() - timedelta(days=3),
                           valid_to=now() - timedelta(days=1)))
        db.commit()
    cyclic = client.get(impact_route, headers=headers, auth=credentials).json()
    assert len(cyclic["items"]) == 2 and cyclic["truncated"] is False

    pid = pipeline_id(client)
    run_id = client.post(f"/api/v1/pipelines/{pid}/runs", headers=headers, auth=credentials,
                         json={"demo_fault": "F04"}).json()["id"]
    assert process_one(settings, "m5-incident-worker")
    incidents = client.get("/api/v1/incidents", headers=headers, auth=credentials).json()["items"]
    incident = next(item for item in incidents if item["run_id"] == run_id)
    linked = client.get(f"/api/v1/incidents/{incident['id']}/impact", headers=viewer_headers,
                        auth=viewer_credentials).json()
    assert linked["incident_id"] == incident["id"]
    assert {item["name"] for item in linked["items"]} == {"demo.revenue_dashboard", "demo.sales_forecast"}
    assert client.get(f"/api/v1/incidents/{incident['id']}/impact", headers=other_headers,
                      auth=other_credentials).status_code == 404


def _event():
    source_a = {"namespace": "test.lineage", "name": "source.a"}
    source_b = {"namespace": "test.lineage", "name": "source.b"}
    target_a = {"namespace": "test.lineage", "name": "target.a"}
    target_b = {"namespace": "test.lineage", "name": "target.b"}
    return {"eventType": "COMPLETE", "eventTime": now().isoformat(), "producer": "https://example.invalid/lineage",
            "run": {"runId": str(uuid4())},
            "job": {"namespace": "test.jobs", "name": "split", "facets": {"lineage": {"entries": [
                {**target_a, "type": "DATASET", "inputs": [{**source_a, "type": "DATASET"}]},
                {**target_b, "type": "DATASET", "inputs": [{**source_b, "type": "DATASET"}]},
            ]}}}, "inputs": [source_a, source_b], "outputs": [target_a, target_b]}


def test_explicit_event_mappings_idempotency_and_authorization(request):
    _, engine = request.getfixturevalue("m5_setup")
    client = TestClient(app)
    headers, credentials = auth()
    viewer_headers, viewer_credentials = auth("demo-a-viewer")
    other_headers, other_credentials = auth("demo-b-executor", "demo-b")
    event = _event()
    route = "/api/v1/lineage/events"
    assert client.post(route, headers=viewer_headers, auth=viewer_credentials, json=event).status_code == 403
    first = client.post(route, headers=headers, auth=credentials, json=event)
    assert first.status_code == 201 and first.json()["edge_count"] == 2
    again = client.post(route, headers=headers, auth=credentials, json=event)
    assert again.json()["id"] == first.json()["id"] and again.json()["edge_count"] == 0
    changed = {**event, "outputs": list(reversed(event["outputs"]))}
    assert client.post(route, headers=headers, auth=credentials, json=changed).status_code == 409
    with Session(engine) as db:
        assert len(db.scalars(select(LineageEvent).where(LineageEvent.id == first.json()["id"])).all()) == 1
        assert len(db.scalars(select(LineageEdge).where(LineageEdge.event_id == first.json()["id"])).all()) == 2
    assets = client.get("/api/v1/assets", headers=headers, auth=credentials).json()["items"]
    refs = {asset["name"]: asset for asset in assets if asset["namespace"] == "test.lineage"}
    result = client.get(f"/api/v1/lineage/{refs['source.a']['id']}/impact", headers=headers,
                        auth=credentials).json()
    assert [item["name"] for item in result["items"]] == ["target.a"]
    assert result["items"][0]["path_edges"][0]["source_label"] == "submitted metadata"
    assert client.get(f"/api/v1/lineage/{refs['source.a']['id']}/impact", headers=other_headers,
                      auth=other_credentials).status_code == 404
    assert client.post(route, headers=other_headers, auth=other_credentials, json=event).status_code == 201


def test_event_validation_and_unknown_lineage(request):
    _, _ = request.getfixturevalue("m5_setup")
    client = TestClient(app)
    headers, credentials = auth()
    event = _event()
    route = "/api/v1/lineage/events"
    assert client.post(route, headers=headers, auth=credentials,
                       json={**event, "tenant_id": "forged"}).status_code == 422
    invalid = _event()
    invalid["job"]["facets"]["lineage"]["entries"][0]["inputs"][0]["name"] = "not-listed"
    assert client.post(route, headers=headers, auth=credentials, json=invalid).status_code == 422
    bad_producer = {**_event(), "producer": "https://user:secret@example.invalid/path?token=secret"}
    assert client.post(route, headers=headers, auth=credentials, json=bad_producer).status_code == 422
    invalid_url = {**_event(), "producer": "https://[invalid"}
    assert client.post(route, headers=headers, auth=credentials, json=invalid_url).status_code == 422
    oversized = _event()
    oversized["job"]["facets"]["unneeded"] = {"filler": "x" * 65_000}
    assert client.post(route, headers=headers, auth=credentials, json=oversized).status_code == 413
    no_mapping = _event()
    no_mapping["job"]["facets"] = {}
    created = client.post(route, headers=headers, auth=credentials, json=no_mapping)
    assert created.status_code == 201 and created.json()["edge_count"] == 0
    assets = client.get("/api/v1/assets", headers=headers, auth=credentials).json()["items"]
    source = next(item for item in assets if item["namespace"] == "test.lineage" and item["name"] == "source.a")
    result = client.get(f"/api/v1/lineage/{source['id']}/impact", headers=headers, auth=credentials).json()
    assert result["impact_status"] == "UNKNOWN" and result["items"] == []
