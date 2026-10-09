"""Durable incident observations and bounded retry scheduling.

Revision ID: 0002_incidents
Revises: 0001_foundation
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_incidents"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("runs", sa.Column("demo_fault", sa.String(3)))
    op.add_column("runs", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("pipeline_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36)),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("provenance", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=False),
        sa.Column("occurrence_count", sa.Integer, nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "pipeline_id"], ["pipelines.tenant_id", "pipelines.id"]),
        sa.ForeignKeyConstraint(["tenant_id", "run_id"], ["runs.tenant_id", "runs.id"]),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "fingerprint"),
    )
    op.create_index("ix_incidents_tenant_last_seen", "incidents", ["tenant_id", "last_seen_at"])
    op.create_table(
        "incident_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(24), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "incident_id"], ["incidents.tenant_id", "incidents.id"]),
    )
    op.create_index("ix_incident_events_timeline", "incident_events", ["incident_id", "occurred_at"])


def downgrade():
    op.drop_index("ix_incident_events_timeline", table_name="incident_events")
    op.drop_table("incident_events")
    op.drop_index("ix_incidents_tenant_last_seen", table_name="incidents")
    op.drop_table("incidents")
    op.drop_column("runs", "next_attempt_at")
    op.drop_column("runs", "demo_fault")
