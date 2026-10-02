"""Conversation memory, Lost & Found time, and learning pipeline.

Revision ID: 0004_conversation_learning
Revises: 0003_store_discovery_metadata
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_conversation_learning"
down_revision = "0003_store_discovery_metadata"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("voice_sessions") as batch:
        batch.add_column(sa.Column("memory_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("last_activity_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("cases") as batch:
        batch.add_column(sa.Column("last_seen_time", sa.String(length=120), nullable=True))

    op.create_table(
        "learning_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_hash", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=False, server_default="web"),
        sa.Column("intent", sa.String(length=120), nullable=False, server_default="unknown"),
        sa.Column("language", sa.String(length=20), nullable=False, server_default="en-NG"),
        sa.Column("topics", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("needs_human", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_learning_interactions_session_hash", "learning_interactions", ["session_hash"])
    op.create_index("ix_learning_interactions_channel", "learning_interactions", ["channel"])
    op.create_index("ix_learning_interactions_intent", "learning_interactions", ["intent"])
    op.create_index("ix_learning_interactions_created_at", "learning_interactions", ["created_at"])

    op.create_table(
        "learning_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(length=80), nullable=False, unique=True),
        sa.Column("model_kind", sa.String(length=80), nullable=False, server_default="ANONYMIZED_PATTERN_V1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="TESTED"),
        sa.Column("training_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evaluation_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pattern_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approved_by", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("tested_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_learning_models_version", "learning_models", ["version"], unique=True)
    op.create_index("ix_learning_models_status", "learning_models", ["status"])
    op.create_index("ix_learning_models_active", "learning_models", ["active"])


def downgrade():
    op.drop_index("ix_learning_models_active", table_name="learning_models")
    op.drop_index("ix_learning_models_status", table_name="learning_models")
    op.drop_index("ix_learning_models_version", table_name="learning_models")
    op.drop_table("learning_models")

    op.drop_index("ix_learning_interactions_created_at", table_name="learning_interactions")
    op.drop_index("ix_learning_interactions_intent", table_name="learning_interactions")
    op.drop_index("ix_learning_interactions_channel", table_name="learning_interactions")
    op.drop_index("ix_learning_interactions_session_hash", table_name="learning_interactions")
    op.drop_table("learning_interactions")

    with op.batch_alter_table("cases") as batch:
        batch.drop_column("last_seen_time")

    with op.batch_alter_table("voice_sessions") as batch:
        batch.drop_column("last_activity_at")
        batch.drop_column("memory_json")
