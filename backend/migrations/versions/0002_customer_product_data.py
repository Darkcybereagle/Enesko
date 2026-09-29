"""Customer product data provenance and optional store mapping.

Revision ID: 0002_customer_product_data
Revises: 0001_category2_baseline
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_customer_product_data"
down_revision = "0001_category2_baseline"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("stores") as batch:
        batch.alter_column(
            "floor_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch.add_column(sa.Column("source_name", sa.String(length=240), nullable=True))
        batch.add_column(sa.Column("source_url", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("verified_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("map_node_code", sa.String(length=80), nullable=True))
        batch.create_index("ix_stores_map_node_code", ["map_node_code"], unique=False)


def downgrade():
    with op.batch_alter_table("stores") as batch:
        batch.drop_index("ix_stores_map_node_code")
        batch.drop_column("map_node_code")
        batch.drop_column("expires_at")
        batch.drop_column("verified_at")
        batch.drop_column("source_url")
        batch.drop_column("source_name")
        batch.alter_column(
            "floor_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
