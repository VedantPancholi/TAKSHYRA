from sqlalchemy import select

from takshyra.auth import hash_password
from takshyra.contracts import SEED_CONTRACT, canonical
from takshyra.config import Settings
from sqlalchemy.orm import Session

from takshyra.db import engine
from takshyra.models import Asset, ContractVersion, Dataset, LineageEdge, Membership, Pipeline, Tenant, User, now


DEMO_ASSETS = (
    ("demo.orders_raw", "DATASET", "demo-data-platform", "MEDIUM"),
    ("demo.orders_curated", "DATASET", "demo-data-platform", "HIGH"),
    ("demo.revenue_dashboard", "DASHBOARD", "demo-analytics", "HIGH"),
    ("demo.sales_forecast", "ML_MODEL", "demo-analytics", "MEDIUM"),
    ("demo.telemetry_raw", "DATASET", "demo-operations", "LOW"),
    ("demo.telemetry_decoded", "DATASET", "demo-operations", "MEDIUM"),
    ("demo.operations_dashboard", "DASHBOARD", "demo-operations", "MEDIUM"),
)
DEMO_EDGES = (
    ("demo.orders_raw", "demo.orders_curated", "DERIVES_FROM"),
    ("demo.orders_curated", "demo.revenue_dashboard", "SERVES"),
    ("demo.orders_curated", "demo.sales_forecast", "SERVES"),
    ("demo.telemetry_raw", "demo.telemetry_decoded", "DERIVES_FROM"),
    ("demo.telemetry_decoded", "demo.operations_dashboard", "SERVES"),
)


def seed_demo_graph(db: Session, tenant_id: str) -> Asset:
    assets = {}
    for name, kind, owner, criticality in DEMO_ASSETS:
        asset = db.scalar(select(Asset).where(
            Asset.tenant_id == tenant_id, Asset.namespace == "takshyra.demo", Asset.name == name,
        ))
        if asset is None:
            asset = Asset(tenant_id=tenant_id, namespace="takshyra.demo", name=name,
                          kind=kind, owner=owner, criticality=criticality, source_label="simulated")
            db.add(asset)
            db.flush()
        assets[name] = asset
    for source, target, relation in DEMO_EDGES:
        existing = db.scalar(select(LineageEdge).where(
            LineageEdge.tenant_id == tenant_id, LineageEdge.source_asset_id == assets[source].id,
            LineageEdge.target_asset_id == assets[target].id, LineageEdge.origin == "declared",
        ))
        if existing is None:
            db.add(LineageEdge(tenant_id=tenant_id, source_asset_id=assets[source].id,
                               target_asset_id=assets[target].id, relation=relation, origin="declared",
                               source_label="simulated", valid_from=now()))
    return assets["demo.orders_curated"]


def seed() -> None:
    settings = Settings.from_env()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL required")
    with Session(engine()) as db:
        for slug in ("demo-a", "demo-b"):
            tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
            if tenant is None:
                tenant = Tenant(slug=slug)
                db.add(tenant)
                db.flush()
            curated_asset = seed_demo_graph(db, tenant.id)
            pipeline = db.scalar(select(Pipeline).where(Pipeline.tenant_id == tenant.id, Pipeline.name == "orders_csv_v1"))
            if pipeline is None:
                pipeline = Pipeline(tenant_id=tenant.id, name="orders_csv_v1", source_kind="seed_orders_v1")
                db.add(pipeline)
            pipeline.output_asset_id = curated_asset.id
            dataset = db.scalar(select(Dataset).where(Dataset.tenant_id == tenant.id, Dataset.ref == "demo.orders_curated"))
            if dataset is None:
                dataset = Dataset(tenant_id=tenant.id, ref="demo.orders_curated", owner="demo-data-platform", active_version=1)
                db.add(dataset)
                db.flush()
                definition, digest = canonical(SEED_CONTRACT)
                db.add(ContractVersion(tenant_id=tenant.id, dataset_id=dataset.id, version=1,
                                       definition_json=definition, definition_hash=digest))
            for suffix, role in (("executor", "executor"), ("viewer", "viewer"), ("approver", "approver")):
                name = f"{slug}-{suffix}"
                user = db.scalar(select(User).where(User.username == name))
                if user is None:
                    user = User(username=name, password_hash=hash_password(settings.demo_passwords[name]))
                    db.add(user)
                    db.flush()
                else:
                    # Seeding also rotates demo passwords when local environment changes.
                    user.password_hash = hash_password(settings.demo_passwords[name])
                if db.get(Membership, (tenant.id, user.id)) is None:
                    db.add(Membership(tenant_id=tenant.id, user_id=user.id, role=role))
        db.commit()


if __name__ == "__main__":
    seed()
