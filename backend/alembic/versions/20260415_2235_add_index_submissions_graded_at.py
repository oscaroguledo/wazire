"""add_index_submissions_graded_at

Revision ID: 2235addidx
Revises: 4de190c98f70
Create Date: 2026-04-15 22:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2235addidx'
down_revision: Union[str, None] = '4de190c98f70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index on graded_at column to speed up graded/pending submission queries
    op.create_index('ix_submissions_graded_at', 'submissions', ['graded_at'], unique=False, schema='academic')


def downgrade() -> None:
    op.drop_index('ix_submissions_graded_at', table_name='submissions', schema='academic')
