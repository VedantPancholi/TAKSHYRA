"""Versioned orders contracts and run contract binding.

Revision ID: 0005_contracts
Revises: 0004_policy_actions
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_contracts"
down_revision = "0004_policy_actions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("ref", sa.String(128), nullable=False),
        sa.Column("owner", sa.String(128), nullable=False),
        sa.Column("active_version", sa.Integer, nullable=False),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "ref"),
    )
    op.create_table(
        "contract_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("definition_json", sa.Text, nullable=False),
        sa.Column("definition_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "dataset_id"], ["datasets.tenant_id", "datasets.id"]),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "dataset_id", "version"),
    )
    with op.batch_alter_table("runs") as batch:
        batch.add_column(sa.Column("contract_version_id", sa.String(36)))
        batch.create_foreign_key("fk_runs_contract_version", "contract_versions",
                                 ["tenant_id", "contract_version_id"], ["tenant_id", "id"])


def downgrade():
    with op.batch_alter_table("runs") as batch:
        batch.drop_constraint("fk_runs_contract_version", type_="foreignkey")
        batch.drop_column("contract_version_id")
    op.drop_table("contract_versions")
    op.drop_table("datasets")
