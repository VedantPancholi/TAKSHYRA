"""Record local diagnosis provider provenance.

Revision ID: 0008_local_ai
Revises: 0007_diagnoses
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_local_ai"
down_revision = "0007_diagnoses"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("diagnoses") as batch:
        batch.add_column(sa.Column("model_id", sa.String(100)))
        batch.add_column(sa.Column("provider_status", sa.String(24)))


def downgrade():
    with op.batch_alter_table("diagnoses") as batch:
        batch.drop_column("provider_status")
        batch.drop_column("model_id")
