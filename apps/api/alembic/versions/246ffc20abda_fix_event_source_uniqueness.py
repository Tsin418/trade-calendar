"""fix_event_source_uniqueness

Revision ID: 246ffc20abda
Revises: 4e280824a414
Create Date: 2026-09-02 12:19:30.172422
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "246ffc20abda"
down_revision: Union[str, Sequence[str], None] = "4e280824a414"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Older builds allowed multiple latest-observation links per event/source.
    # Keep the primary or most recently verified link before tightening the invariant.
    op.execute(sa.text("""
        DELETE FROM event_sources
        WHERE id IN (
            SELECT id FROM (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY event_id, source_id
                        ORDER BY
                            is_primary DESC,
                            (last_verified_at IS NOT NULL) DESC,
                            last_verified_at DESC,
                            updated_at DESC,
                            id DESC
                    ) AS row_number
                FROM event_sources
            ) AS ranked
            WHERE row_number > 1
        )
    """))
    with op.batch_alter_table("event_sources", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("uq_event_sources_event_id"), type_="unique")
        batch_op.create_unique_constraint(
            "uq_event_sources_event_source", ["event_id", "source_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("event_sources", schema=None) as batch_op:
        batch_op.drop_constraint("uq_event_sources_event_source", type_="unique")
        batch_op.create_unique_constraint(
            batch_op.f("uq_event_sources_event_id"),
            ["event_id", "source_id", "observation_id"],
        )
