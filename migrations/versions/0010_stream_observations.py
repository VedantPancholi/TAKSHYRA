"""Persist bounded local stream observations.

Revision ID: 0010_stream_observations
Revises: 0009_shadow_recovery
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_stream_observations"
down_revision = "0009_shadow_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stream_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("pipeline_id", sa.String(36), nullable=False),
        sa.Column("scenario", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("metrics_json", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "pipeline_id"], ["pipelines.tenant_id", "pipelines.id"]),
    )
    op.create_index("ix_stream_observations_tenant_created", "stream_observations", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_stream_observations_tenant_created", table_name="stream_observations")
    op.drop_table("stream_observations")
