"""Bind ADF pipelines and persist normalized run observations.

Revision ID: 0011_adf_run_observations
Revises: 0010_stream_observations
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_adf_run_observations"
down_revision = "0010_stream_observations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adf_pipeline_bindings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("pipeline_id", sa.String(36), nullable=False),
        sa.Column("factory", sa.String(192), nullable=False),
        sa.Column("external_name", sa.String(128), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "pipeline_id"], ["pipelines.tenant_id", "pipelines.id"]),
        sa.UniqueConstraint("tenant_id", "pipeline_id"),
        sa.UniqueConstraint("tenant_id", "factory", "external_name"),
    )
    op.create_table(
        "adf_run_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("pipeline_id", sa.String(36), nullable=False),
        sa.Column("factory", sa.String(192), nullable=False),
        sa.Column("external_run_id", sa.String(128), nullable=False),
        sa.Column("external_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("provenance", sa.String(16), nullable=False),
        sa.Column("run_start", sa.DateTime(timezone=True)),
        sa.Column("run_end", sa.DateTime(timezone=True)),
        sa.Column("failure_reported", sa.Boolean, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "pipeline_id"], ["pipelines.tenant_id", "pipelines.id"]),
        sa.UniqueConstraint("tenant_id", "factory", "external_run_id"),
    )
    op.create_index(
        "ix_adf_run_observations_tenant_seen", "adf_run_observations", ["tenant_id", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_adf_run_observations_tenant_seen", table_name="adf_run_observations")
    op.drop_table("adf_run_observations")
    op.drop_table("adf_pipeline_bindings")
