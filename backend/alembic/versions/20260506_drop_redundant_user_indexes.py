"""drop redundant user indexes

Revision ID: 20260506_drop_redundant_user_indexes
Revises: 50523919eb00
Create Date: 2026-05-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260506_drop_redundant_user_indexes'
down_revision = '50523919eb00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop redundant single-column indexes if they exist (Postgres IF EXISTS)
    op.execute("DROP INDEX IF EXISTS account.ix_users_email")
    op.execute("DROP INDEX IF EXISTS account.ix_users_role")
    op.execute("DROP INDEX IF EXISTS account.ix_users_is_active")


def downgrade() -> None:
    # Recreate the dropped indexes on downgrade
    op.create_index('ix_users_email', 'users', ['email'], unique=False, schema='account')
    op.create_index('ix_users_role', 'users', ['role'], unique=False, schema='account')
    op.create_index('ix_users_is_active', 'users', ['is_active'], unique=False, schema='account')
