"""Persist Agnes translations without modifying source records."""

from alembic import op
import sqlalchemy as sa

revision = "9c42b518ad70"
down_revision = "8b6c7d1e2f30"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "text_translations",
        sa.Column("text_hash", sa.String(64), primary_key=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("target_language", sa.String(16), nullable=False),
        sa.Column("translated_text", sa.Text()),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(100)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_text_translations_status", "text_translations", ["status"])


def downgrade():
    op.drop_index("ix_text_translations_status", table_name="text_translations")
    op.drop_table("text_translations")
