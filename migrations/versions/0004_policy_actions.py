"""Policy-gated local action proposals, effects and timeline.

Revision ID: 0004_policy_actions
Revises: 0003_incident_owner
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_policy_actions"
down_revision = "0003_incident_owner"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("runs") as batch:
        batch.add_column(sa.Column("retry_of_run_id", sa.String(36)))
        batch.create_foreign_key("fk_runs_retry_source", "runs", ["retry_of_run_id"], ["id"])
        batch.create_unique_constraint("uq_runs_retry_source", ["retry_of_run_id"])
    op.add_column("incident_events", sa.Column("safe_detail", sa.String(256)))
    op.create_table(
        "action_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("requester_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approver_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("parameters_json", sa.Text, nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("policy_decision", sa.String(24), nullable=False),
        sa.Column("policy_reason", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approved_digest", sa.String(64)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("verification_status", sa.String(16)),
        sa.Column("effect_ref_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key"),
    )
    op.create_index("ix_action_proposals_tenant_created", "action_proposals", ["tenant_id", "created_at"])
    op.create_table(
        "action_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("proposal_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "proposal_id"], ["action_proposals.tenant_id", "action_proposals.id"]),
    )
    op.create_index("ix_action_events_timeline", "action_events", ["proposal_id", "occurred_at"])
    op.create_table(
        "action_effects",
        sa.Column("proposal_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("effect_kind", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("safe_detail", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "proposal_id"], ["action_proposals.tenant_id", "action_proposals.id"]),
    )


def downgrade():
    op.drop_table("action_effects")
    op.drop_index("ix_action_events_timeline", table_name="action_events")
    op.drop_table("action_events")
    op.drop_index("ix_action_proposals_tenant_created", table_name="action_proposals")
    op.drop_table("action_proposals")
    op.drop_column("incident_events", "safe_detail")
    with op.batch_alter_table("runs") as batch:
        batch.drop_constraint("uq_runs_retry_source", type_="unique")
        batch.drop_constraint("fk_runs_retry_source", type_="foreignkey")
        batch.drop_column("retry_of_run_id")
