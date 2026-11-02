"""Tenant-scoped asset graph and lineage event identities.

Revision ID: 0006_lineage
Revises: 0005_contracts
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_lineage"
down_revision = "0005_contracts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("namespace", sa.String(128), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("owner", sa.String(128), nullable=False),
        sa.Column("criticality", sa.String(16), nullable=False),
        sa.Column("source_label", sa.String(24), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "namespace", "name"),
    )
    op.create_index("ix_assets_tenant_kind", "assets", ["tenant_id", "kind"])
    op.create_table(
        "lineage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_key", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("producer", sa.String(256), nullable=False),
        sa.Column("job_namespace", sa.String(128), nullable=False),
        sa.Column("job_name", sa.String(128), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "event_key"),
    )
    op.create_table(
        "lineage_edges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("source_asset_id", sa.String(36), nullable=False),
        sa.Column("target_asset_id", sa.String(36), nullable=False),
        sa.Column("relation", sa.String(24), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("source_label", sa.String(24), nullable=False),
        sa.Column("event_id", sa.String(36)),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.ForeignKeyConstraint(["tenant_id", "source_asset_id"], ["assets.tenant_id", "assets.id"]),
        sa.ForeignKeyConstraint(["tenant_id", "target_asset_id"], ["assets.tenant_id", "assets.id"]),
        sa.ForeignKeyConstraint(["tenant_id", "event_id"], ["lineage_events.tenant_id", "lineage_events.id"]),
    )
    op.create_index("ix_lineage_edges_source", "lineage_edges", ["tenant_id", "source_asset_id", "valid_to"])
    with op.batch_alter_table("pipelines") as batch:
        batch.add_column(sa.Column("output_asset_id", sa.String(36)))
        batch.create_foreign_key("fk_pipelines_output_asset", "assets", ["tenant_id", "output_asset_id"],
                                 ["tenant_id", "id"])


def downgrade():
    with op.batch_alter_table("pipelines") as batch:
        batch.drop_constraint("fk_pipelines_output_asset", type_="foreignkey")
        batch.drop_column("output_asset_id")
    op.drop_index("ix_lineage_edges_source", table_name="lineage_edges")
    op.drop_table("lineage_edges")
    op.drop_table("lineage_events")
    op.drop_index("ix_assets_tenant_kind", table_name="assets")
    op.drop_table("assets")
