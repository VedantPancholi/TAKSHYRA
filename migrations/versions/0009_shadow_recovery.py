"""Record isolated local shadow replays and independently checked outcomes.

Revision ID: 0009_shadow_recovery
Revises: 0008_local_ai
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_shadow_recovery"
down_revision = "0008_local_ai"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shadow_replays",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=False),
        sa.Column("source_run_id", sa.String(36), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("contract_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("baseline_row_count", sa.Integer),
        sa.Column("replay_row_count", sa.Integer),
        sa.Column("replay_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "incident_id"], ["incidents.tenant_id", "incidents.id"]),
        sa.ForeignKeyConstraint(["tenant_id", "source_run_id"], ["runs.tenant_id", "runs.id"]),
        sa.UniqueConstraint("tenant_id", "id"),
    )
    op.create_index("ix_shadow_replays_incident", "shadow_replays", ["tenant_id", "incident_id", "created_at"])
    op.create_table(
        "recovery_outcomes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=False),
        sa.Column("proposal_id", sa.String(36), nullable=False),
        sa.Column("recovery_run_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("manifest_sha256", sa.String(64)),
        sa.Column("verified_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "incident_id"], ["incidents.tenant_id", "incidents.id"]),
        sa.ForeignKeyConstraint(["tenant_id", "proposal_id"], ["action_proposals.tenant_id", "action_proposals.id"]),
        sa.ForeignKeyConstraint(["tenant_id", "recovery_run_id"], ["runs.tenant_id", "runs.id"]),
        sa.UniqueConstraint("tenant_id", "proposal_id"),
    )


def downgrade():
    op.drop_table("recovery_outcomes")
    op.drop_index("ix_shadow_replays_incident", table_name="shadow_replays")
    op.drop_table("shadow_replays")
