"""Foundation schema.

Revision ID: 0001_foundation
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("tenants", sa.Column("id", sa.String(36), primary_key=True), sa.Column("slug", sa.String(64), nullable=False, unique=True))
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("username", sa.String(64), nullable=False, unique=True), sa.Column("password_hash", sa.String(256), nullable=False))
    op.create_table("memberships", sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True), sa.Column("role", sa.String(16), nullable=False))
    op.create_table("pipelines", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("name", sa.String(64), nullable=False), sa.Column("source_kind", sa.String(32), nullable=False), sa.UniqueConstraint("tenant_id", "id"), sa.UniqueConstraint("tenant_id", "name"))
    op.create_table("runs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("pipeline_id", sa.String(36), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("payload_digest", sa.String(64), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("quality_status", sa.String(16), nullable=False), sa.Column("publication_status", sa.String(16), nullable=False), sa.Column("lease_owner", sa.String(64)), sa.Column("lease_until", sa.DateTime(timezone=True)), sa.Column("row_count", sa.Integer), sa.Column("manifest_path", sa.String(512)), sa.Column("error_code", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.ForeignKeyConstraint(["tenant_id", "pipeline_id"], ["pipelines.tenant_id", "pipelines.id"]), sa.UniqueConstraint("tenant_id", "id"), sa.UniqueConstraint("tenant_id", "idempotency_key"))
    op.create_index("ix_runs_claim", "runs", ["status", "lease_until"])
    op.create_table("attempts", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), nullable=False), sa.Column("run_id", sa.String(36), nullable=False), sa.Column("number", sa.Integer, nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("error_code", sa.String(64)), sa.ForeignKeyConstraint(["tenant_id", "run_id"], ["runs.tenant_id", "runs.id"]), sa.UniqueConstraint("run_id", "number"))
    op.create_table("quality_results", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), nullable=False), sa.Column("run_id", sa.String(36), nullable=False), sa.Column("rule_id", sa.String(64), nullable=False), sa.Column("rule_version", sa.Integer, nullable=False), sa.Column("outcome", sa.String(16), nullable=False), sa.Column("expected", sa.String(128), nullable=False), sa.Column("observed", sa.String(128), nullable=False), sa.ForeignKeyConstraint(["tenant_id", "run_id"], ["runs.tenant_id", "runs.id"]))
    op.create_table("audit_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("action", sa.String(64), nullable=False), sa.Column("target_id", sa.String(36), nullable=False), sa.Column("outcome", sa.String(16), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("safe_detail", sa.Text, nullable=False))


def downgrade():
    for table in ("audit_events", "quality_results", "attempts", "runs", "pipelines", "memberships", "users", "tenants"):
        op.drop_table(table)
