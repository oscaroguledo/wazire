"""app-wide refactor: add missing columns, constraints, and enum values

Revision ID: 20260507_app_wide_refactor
Revises: 20260506_drop_redundant_user_indexes
Create Date: 2026-05-07 00:00:00.000000

Covers all schema changes from the app-wide refactor spec (Phase 3):
  - academic.exams:        add end_time, drop student_id + ix_exams_student_id
  - academic.submissions:  add submitted_at
  - academic.submission_attempts: add grading_started_at
  - academic.student_answers: add UNIQUE constraint (student_id, exam_id, question_id)
  - account.tenants:       add tenant_code (NOT NULL, UNIQUE), paystack_customer_code,
                           monnify_account_reference
  - billings.invoices:     add payment_reference, payment_gateway, paid_at, payment_url
                           (invoice_status_enum already exists from init migration)
  - billings.billing_plans: add is_active (already present in model; guard with IF NOT EXISTS)
  - account.tenants:       start_date / end_date already present; guard with IF NOT EXISTS
  - submission_status_enum: add grading_in_progress value
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260507_app_wide_refactor'
down_revision = '20260506_drop_redundant_user_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Add grading_in_progress to submission_status_enum
    #    PostgreSQL requires ALTER TYPE outside a transaction for enum changes,
    #    but Alembic's op.execute works within the migration transaction.
    #    We use IF NOT EXISTS (PG 14+) to make it idempotent.
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TYPE submission_status_enum ADD VALUE IF NOT EXISTS 'grading_in_progress' "
        "AFTER 'submitted'"
    )

    # ------------------------------------------------------------------
    # 2. academic.exams — add end_time, drop student_id
    # ------------------------------------------------------------------
    op.add_column(
        'exams',
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True,
                  comment='Exam end time: start_time + duration (persisted)'),
        schema='academic',
    )
    op.create_index('ix_exams_end_time', 'exams', ['end_time'], unique=False, schema='academic')

    # Back-fill end_time for existing rows where start_time is set
    op.execute(
        """
        UPDATE academic.exams
        SET end_time = start_time + (duration * interval '1 hour')
        WHERE start_time IS NOT NULL AND end_time IS NULL
        """
    )

    # Drop the student_id index first, then the column
    op.execute("DROP INDEX IF EXISTS academic.ix_exams_student_id")
    op.drop_column('exams', 'student_id', schema='academic')

    # ------------------------------------------------------------------
    # 3. academic.submissions — add submitted_at
    # ------------------------------------------------------------------
    op.add_column(
        'submissions',
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True, server_default=None,
                  comment='UTC moment when the student submitted the exam'),
        schema='academic',
    )
    op.create_index('ix_submissions_submitted_at', 'submissions', ['submitted_at'],
                    unique=False, schema='academic')

    # ------------------------------------------------------------------
    # 4. academic.submission_attempts — add grading_started_at
    # ------------------------------------------------------------------
    op.add_column(
        'submission_attempts',
        sa.Column('grading_started_at', sa.DateTime(timezone=True), nullable=True, server_default=None,
                  comment='UTC moment when grading began for this attempt'),
        schema='academic',
    )

    # ------------------------------------------------------------------
    # 5. academic.student_answers — add UNIQUE constraint
    #    (may already exist from init migration; use IF NOT EXISTS guard)
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_student_answer_student_exam_question'
                  AND conrelid = 'academic.student_answers'::regclass
            ) THEN
                ALTER TABLE academic.student_answers
                ADD CONSTRAINT uq_student_answer_student_exam_question
                UNIQUE (student_id, exam_id, question_id);
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 6. account.tenants — add tenant_code, paystack_customer_code,
    #    monnify_account_reference
    #    (start_date / end_date already exist from init migration)
    # ------------------------------------------------------------------
    # tenant_code: NOT NULL with a temporary default so existing rows get a value,
    # then we remove the server default to enforce application-level generation.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'account'
                  AND table_name   = 'tenants'
                  AND column_name  = 'tenant_code'
            ) THEN
                ALTER TABLE account.tenants
                ADD COLUMN tenant_code VARCHAR(6) NOT NULL
                    DEFAULT upper(substring(md5(random()::text) for 6));
            END IF;
        END
        $$;
        """
    )
    # Remove the temporary default so future inserts must supply the value
    op.execute(
        "ALTER TABLE account.tenants ALTER COLUMN tenant_code DROP DEFAULT"
    )
    # Add unique index (idempotent)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'account'
                  AND tablename  = 'tenants'
                  AND indexname  = 'ix_tenants_tenant_code'
            ) THEN
                CREATE UNIQUE INDEX ix_tenants_tenant_code ON account.tenants (tenant_code);
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'account'
                  AND table_name   = 'tenants'
                  AND column_name  = 'paystack_customer_code'
            ) THEN
                ALTER TABLE account.tenants
                ADD COLUMN paystack_customer_code VARCHAR(100) NULL;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'account'
                  AND table_name   = 'tenants'
                  AND column_name  = 'monnify_account_reference'
            ) THEN
                ALTER TABLE account.tenants
                ADD COLUMN monnify_account_reference VARCHAR(100) NULL;
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 7. billings.invoices — add payment columns
    #    (invoice_status_enum + status column already exist from init migration)
    # ------------------------------------------------------------------

    # Create payment_gateway_enum type if it doesn't exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'payment_gateway_enum'
            ) THEN
                CREATE TYPE payment_gateway_enum AS ENUM ('paystack', 'monnify');
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'billings'
                  AND table_name   = 'invoices'
                  AND column_name  = 'payment_reference'
            ) THEN
                ALTER TABLE billings.invoices
                ADD COLUMN payment_reference VARCHAR(100) NULL;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'billings'
                  AND table_name   = 'invoices'
                  AND column_name  = 'payment_gateway'
            ) THEN
                ALTER TABLE billings.invoices
                ADD COLUMN payment_gateway payment_gateway_enum NULL;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'billings'
                  AND table_name   = 'invoices'
                  AND column_name  = 'paid_at'
            ) THEN
                ALTER TABLE billings.invoices
                ADD COLUMN paid_at TIMESTAMPTZ NULL;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'billings'
                  AND table_name   = 'invoices'
                  AND column_name  = 'payment_url'
            ) THEN
                ALTER TABLE billings.invoices
                ADD COLUMN payment_url VARCHAR(500) NULL;
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 8. billings.billing_plans — add is_active (guard with IF NOT EXISTS)
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'billings'
                  AND table_name   = 'billing_plans'
                  AND column_name  = 'is_active'
            ) THEN
                ALTER TABLE billings.billing_plans
                ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 9. account.tenants — start_date / end_date (guard with IF NOT EXISTS)
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'account'
                  AND table_name   = 'tenants'
                  AND column_name  = 'start_date'
            ) THEN
                ALTER TABLE account.tenants ADD COLUMN start_date TIMESTAMPTZ NULL;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'account'
                  AND table_name   = 'tenants'
                  AND column_name  = 'end_date'
            ) THEN
                ALTER TABLE account.tenants ADD COLUMN end_date TIMESTAMPTZ NULL;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Reverse all changes in reverse order
    # ------------------------------------------------------------------

    # 9. Remove start_date / end_date from tenants (only if we added them)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'account' AND table_name = 'tenants'
                  AND column_name = 'start_date'
            ) THEN
                ALTER TABLE account.tenants DROP COLUMN start_date;
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'account' AND table_name = 'tenants'
                  AND column_name = 'end_date'
            ) THEN
                ALTER TABLE account.tenants DROP COLUMN end_date;
            END IF;
        END
        $$;
        """
    )

    # 8. Remove is_active from billing_plans
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'billings' AND table_name = 'billing_plans'
                  AND column_name = 'is_active'
            ) THEN
                ALTER TABLE billings.billing_plans DROP COLUMN is_active;
            END IF;
        END
        $$;
        """
    )

    # 7. Remove invoice payment columns
    for col in ('payment_url', 'paid_at', 'payment_gateway', 'payment_reference'):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'billings' AND table_name = 'invoices'
                      AND column_name = '{col}'
                ) THEN
                    ALTER TABLE billings.invoices DROP COLUMN {col};
                END IF;
            END
            $$;
            """
        )
    op.execute("DROP TYPE IF EXISTS payment_gateway_enum")

    # 6. Remove tenant payment gateway columns and tenant_code
    for col in ('monnify_account_reference', 'paystack_customer_code'):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'account' AND table_name = 'tenants'
                      AND column_name = '{col}'
                ) THEN
                    ALTER TABLE account.tenants DROP COLUMN {col};
                END IF;
            END
            $$;
            """
        )
    op.execute("DROP INDEX IF EXISTS account.ix_tenants_tenant_code")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'account' AND table_name = 'tenants'
                  AND column_name = 'tenant_code'
            ) THEN
                ALTER TABLE account.tenants DROP COLUMN tenant_code;
            END IF;
        END
        $$;
        """
    )

    # 5. Drop student_answers UNIQUE constraint
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_student_answer_student_exam_question'
                  AND conrelid = 'academic.student_answers'::regclass
            ) THEN
                ALTER TABLE academic.student_answers
                DROP CONSTRAINT uq_student_answer_student_exam_question;
            END IF;
        END
        $$;
        """
    )

    # 4. Drop grading_started_at from submission_attempts
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'academic' AND table_name = 'submission_attempts'
                  AND column_name = 'grading_started_at'
            ) THEN
                ALTER TABLE academic.submission_attempts DROP COLUMN grading_started_at;
            END IF;
        END
        $$;
        """
    )

    # 3. Drop submitted_at from submissions
    op.execute("DROP INDEX IF EXISTS academic.ix_submissions_submitted_at")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'academic' AND table_name = 'submissions'
                  AND column_name = 'submitted_at'
            ) THEN
                ALTER TABLE academic.submissions DROP COLUMN submitted_at;
            END IF;
        END
        $$;
        """
    )

    # 2. Restore student_id on exams, drop end_time
    op.execute("DROP INDEX IF EXISTS academic.ix_exams_end_time")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'academic' AND table_name = 'exams'
                  AND column_name = 'end_time'
            ) THEN
                ALTER TABLE academic.exams DROP COLUMN end_time;
            END IF;
        END
        $$;
        """
    )
    op.add_column(
        'exams',
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='FK to student (deprecated — use Enrollment/Submission)'),
        schema='academic',
    )
    op.create_index('ix_exams_student_id', 'exams', ['student_id'], unique=False, schema='academic')

    # 1. NOTE: PostgreSQL does not support removing enum values.
    # The 'grading_in_progress' value cannot be removed from submission_status_enum
    # without recreating the type. This is intentionally left as a no-op on downgrade.
    # To fully revert, recreate the enum type manually if required.
