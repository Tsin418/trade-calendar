"""add event date ranges

Revision ID: 8b6c7d1e2f30
Revises: 246ffc20abda
Create Date: 2026-09-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b6c7d1e2f30"
down_revision: Union[str, Sequence[str], None] = "246ffc20abda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("date_range_start", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("date_range_end", sa.Date(), nullable=True))
        batch_op.create_index(
            "ix_events_date_range", ["date_range_start", "date_range_end"], unique=False
        )
    with op.batch_alter_table("source_observations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("date_range_start", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("date_range_end", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("source_observations", schema=None) as batch_op:
        batch_op.drop_column("date_range_end")
        batch_op.drop_column("date_range_start")
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_index("ix_events_date_range")
        batch_op.drop_column("date_range_end")
        batch_op.drop_column("date_range_start")
