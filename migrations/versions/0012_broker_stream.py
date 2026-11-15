"""Durable local broker checkpoints and idempotent event ledger.

Revision ID: 0012_broker_stream
Revises: 0011_adf_run_observations
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_broker_stream"
down_revision = "0011_adf_run_observations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_checkpoints",
        sa.Column("stream_key", sa.String(128), primary_key=True),
        sa.Column("last_id", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("INSERT INTO broker_checkpoints (stream_key, last_id, updated_at) VALUES ('takshyra:telemetry:local:v1', '0-0', CURRENT_TIMESTAMP)")
    op.create_table(
        "broker_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("pipeline_id", sa.String(36), nullable=False),
        sa.Column("stream_id", sa.String(64), nullable=False, unique=True),
        sa.Column("event_key", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(64)),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "pipeline_id"], ["pipelines.tenant_id", "pipelines.id"]),
        sa.UniqueConstraint("tenant_id", "pipeline_id", "event_key"),
    )
    op.create_index("ix_broker_events_tenant_created", "broker_events", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_broker_events_tenant_created", table_name="broker_events")
    op.drop_table("broker_events")
    op.drop_table("broker_checkpoints")
