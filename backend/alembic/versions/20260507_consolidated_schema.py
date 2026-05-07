"""Consolidated migration: create the full current schema from model metadata

This destructive consolidation replaces prior individual revision files.

NOTE: This migration is intended for bootstrapping new databases. If your
database already has previous alembic revisions applied, you should either
run `alembic stamp <revision>` to align history appropriately or drop/reset
the database before applying this migration. Proceed with caution in
production environments.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260507_consolidated'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables by reflecting current model metadata.

    This calls `Base.metadata.create_all()` to create the database schema
    as defined by the SQLAlchemy models currently imported by Alembic's
    env.py (which sets `target_metadata = Base.metadata`).
    """
    # Import here so Alembic's env.py has already configured sys.path and
    # registered models with Base.metadata.
    from core.database import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all tables created by `upgrade()`.

    This is destructive: it will remove the application's tables. Use only
    for local testing or controlled rollbacks.
    """
    from core.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
