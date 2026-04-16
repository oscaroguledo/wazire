"""add_dashboard_indexes

Revision ID: 4e2a993f6067
Revises: 2235addidx
Create Date: 2026-04-15 23:05:15.766070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e2a993f6067'
down_revision: Union[str, None] = '2235addidx'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add indexes to dashboard tables if they don't exist
    # Use op.execute with IF NOT EXISTS to avoid errors if indexes already exist
    
    # Lecturer dashboard index
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'ix_lecturer_dashboard_lecturer_id'
                AND schemaname = 'analytics'
            ) THEN
                CREATE INDEX ix_lecturer_dashboard_lecturer_id 
                ON analytics.lecturer_dashboard (lecturer_id);
            END IF;
        END $$;
    """)
    
    # Admin dashboard index
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'ix_admin_dashboard_admin_id'
                AND schemaname = 'analytics'
            ) THEN
                CREATE INDEX ix_admin_dashboard_admin_id 
                ON analytics.admin_dashboard (admin_id);
            END IF;
        END $$;
    """)
    
    # Student dashboard index
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'ix_student_dashboard_student_id'
                AND schemaname = 'analytics'
            ) THEN
                CREATE INDEX ix_student_dashboard_student_id 
                ON analytics.student_dashboard (student_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Remove indexes
    op.drop_index('ix_lecturer_dashboard_lecturer_id', table_name='lecturer_dashboard', schema='analytics')
    op.drop_index('ix_admin_dashboard_admin_id', table_name='admin_dashboard', schema='analytics')
    op.drop_index('ix_student_dashboard_student_id', table_name='student_dashboard', schema='analytics')
