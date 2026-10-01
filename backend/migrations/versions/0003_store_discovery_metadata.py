"""Store discovery priority and evidence confidence.

Revision ID: 0003_store_discovery_metadata
Revises: 0002_customer_product_data
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_store_discovery_metadata"
down_revision = "0002_customer_product_data"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("stores") as batch:
        batch.add_column(sa.Column("discovery_priority", sa.Integer(), nullable=False, server_default="50"))
        batch.add_column(sa.Column("verification_confidence", sa.String(length=20), nullable=False, server_default="MEDIUM"))
        batch.add_column(sa.Column("location_confidence", sa.String(length=30), nullable=False, server_default="UNMAPPED"))
        batch.add_column(sa.Column("public_rating", sa.Float(), nullable=True))
        batch.add_column(sa.Column("public_review_count", sa.Integer(), nullable=True))
        batch.create_index("ix_stores_discovery_priority", ["discovery_priority"], unique=False)


def downgrade():
    with op.batch_alter_table("stores") as batch:
        batch.drop_index("ix_stores_discovery_priority")
        batch.drop_column("public_review_count")
        batch.drop_column("public_rating")
        batch.drop_column("location_confidence")
        batch.drop_column("verification_confidence")
        batch.drop_column("discovery_priority")
