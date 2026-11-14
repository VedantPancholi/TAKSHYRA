"""Persist evidence-linked diagnosis revisions.

Revision ID: 0007_diagnoses
Revises: 0006_lineage
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_diagnoses"
down_revision = "0006_lineage"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "diagnoses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("method", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("hypotheses_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "incident_id"], ["incidents.tenant_id", "incidents.id"]),
        sa.UniqueConstraint("tenant_id", "incident_id", "evidence_hash"),
    )
    op.create_index("ix_diagnoses_incident_created", "diagnoses", ["tenant_id", "incident_id", "created_at"])


def downgrade():
    op.drop_index("ix_diagnoses_incident_created", table_name="diagnoses")
    op.drop_table("diagnoses")
