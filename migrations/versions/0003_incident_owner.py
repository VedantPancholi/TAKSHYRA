"""Add incident investigation owner.

Revision ID: 0003_incident_owner
Revises: 0002_incidents
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_incident_owner"
down_revision = "0002_incidents"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("incidents") as batch:
        batch.add_column(sa.Column("owner_id", sa.String(36)))
        batch.create_foreign_key("fk_incidents_owner_users", "users", ["owner_id"], ["id"])


def downgrade():
    with op.batch_alter_table("incidents") as batch:
        batch.drop_constraint("fk_incidents_owner_users", type_="foreignkey")
        batch.drop_column("owner_id")
