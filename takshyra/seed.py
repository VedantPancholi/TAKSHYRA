from sqlalchemy import select

from takshyra.auth import hash_password
from takshyra.contracts import SEED_CONTRACT, canonical
from takshyra.config import Settings
from sqlalchemy.orm import Session

from takshyra.db import engine
from takshyra.models import ContractVersion, Dataset, Membership, Pipeline, Tenant, User


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
            if not db.scalar(select(Pipeline).where(Pipeline.tenant_id == tenant.id, Pipeline.name == "orders_csv_v1")):
                db.add(Pipeline(tenant_id=tenant.id, name="orders_csv_v1", source_kind="seed_orders_v1"))
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
