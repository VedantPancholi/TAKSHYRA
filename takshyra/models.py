import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Index, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime, Integer, String, Text


def now() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)


class Pipeline(Base):
    __tablename__ = "pipelines"
    __table_args__ = (UniqueConstraint("tenant_id", "id"), UniqueConstraint("tenant_id", "name"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="seed_orders_v1")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "pipeline_id"], ["pipelines.tenant_id", "pipelines.id"]),
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "idempotency_key"),
        Index("ix_runs_claim", "status", "lease_until"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    pipeline_id: Mapped[str] = mapped_column(String(36), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="QUEUED")
    quality_status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    publication_status: Mapped[str] = mapped_column(String(16), nullable=False, default="HELD")
    lease_owner: Mapped[str | None] = mapped_column(String(64))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_count: Mapped[int | None] = mapped_column(Integer)
    manifest_path: Mapped[str | None] = mapped_column(String(512))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "run_id"], ["runs.tenant_id", "runs.id"]),
        UniqueConstraint("run_id", "number"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))


class QualityResult(Base):
    __tablename__ = "quality_results"
    __table_args__ = (ForeignKeyConstraint(["tenant_id", "run_id"], ["runs.tenant_id", "runs.id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, default=1)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    expected: Mapped[str] = mapped_column(String(128), nullable=False)
    observed: Mapped[str] = mapped_column(String(128), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    safe_detail: Mapped[str] = mapped_column(Text, default="{}")
