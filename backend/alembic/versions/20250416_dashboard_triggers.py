"""Add triggers to auto-update dashboard tables

Revision ID: dashboard_triggers
Revises: 
Create Date: 2025-04-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dashboard_triggers'
down_revision = '50523919eb00'
branch_labels = None
depends_on = None


def upgrade():
    # Create function to update lecturer dashboard
    op.execute("""
        CREATE OR REPLACE FUNCTION update_lecturer_dashboard()
        RETURNS TRIGGER AS $$
        DECLARE
            v_lecturer_id UUID;
        BEGIN
            -- Resolve lecturer_id based on the triggering table
            CASE TG_TABLE_NAME
                WHEN 'courses' THEN
                    IF TG_OP = 'DELETE' THEN v_lecturer_id := OLD.lecturer_id;
                    ELSE v_lecturer_id := NEW.lecturer_id;
                    END IF;
                WHEN 'exams' THEN
                    IF TG_OP = 'DELETE' THEN
                        v_lecturer_id := (SELECT lecturer_id FROM academic.courses WHERE id = OLD.course_id);
                    ELSE
                        v_lecturer_id := (SELECT lecturer_id FROM academic.courses WHERE id = NEW.course_id);
                    END IF;
                WHEN 'enrollments' THEN
                    IF TG_OP = 'DELETE' THEN
                        v_lecturer_id := (SELECT lecturer_id FROM academic.courses WHERE id = OLD.course_id);
                    ELSE
                        v_lecturer_id := (SELECT lecturer_id FROM academic.courses WHERE id = NEW.course_id);
                    END IF;
                WHEN 'submissions' THEN
                    v_lecturer_id := (SELECT c.lecturer_id FROM academic.courses c JOIN academic.exams e ON c.id = e.course_id WHERE e.id = NEW.exam_id);
                ELSE
                    RETURN NEW;
            END CASE;

            IF v_lecturer_id IS NULL THEN
                RETURN NEW;
            END IF;

            INSERT INTO analytics.lecturer_dashboard (id, lecturer_id, total_courses, total_exams, total_students, active_courses, pending_submissions, graded_submissions, created_at, updated_at)
            SELECT 
                gen_random_uuid(),
                v_lecturer_id,
                (SELECT COUNT(*) FROM academic.courses WHERE lecturer_id = v_lecturer_id),
                (SELECT COUNT(*) FROM academic.exams e JOIN academic.courses c ON e.course_id = c.id WHERE c.lecturer_id = v_lecturer_id),
                (SELECT COUNT(DISTINCT student_id) FROM academic.enrollments e JOIN academic.courses c ON e.course_id = c.id WHERE c.lecturer_id = v_lecturer_id),
                (SELECT COUNT(DISTINCT c.id) FROM academic.courses c 
                 WHERE c.lecturer_id = v_lecturer_id 
                 AND EXISTS (SELECT 1 FROM academic.enrollments WHERE course_id = c.id) 
                 OR EXISTS (SELECT 1 FROM academic.exams WHERE course_id = c.id)),
                (SELECT COUNT(*) FROM academic.submissions s 
                 JOIN academic.exams e ON s.exam_id = e.id 
                 JOIN academic.courses c ON e.course_id = c.id 
                 WHERE c.lecturer_id = v_lecturer_id AND s.graded_at IS NULL AND s.attempts_count > 0),
                (SELECT COUNT(*) FROM academic.submissions s 
                 JOIN academic.exams e ON s.exam_id = e.id 
                 JOIN academic.courses c ON e.course_id = c.id 
                 WHERE c.lecturer_id = v_lecturer_id AND s.graded_at IS NOT NULL),
                NOW(),
                NOW()
            ON CONFLICT (lecturer_id) DO UPDATE SET
                total_courses = EXCLUDED.total_courses,
                total_exams = EXCLUDED.total_exams,
                total_students = EXCLUDED.total_students,
                active_courses = EXCLUDED.active_courses,
                pending_submissions = EXCLUDED.pending_submissions,
                graded_submissions = EXCLUDED.graded_submissions,
                updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create function to update student dashboard
    op.execute("""
        CREATE OR REPLACE FUNCTION update_student_dashboard()
        RETURNS TRIGGER AS $$
        DECLARE
            v_student_id UUID;
        BEGIN
            -- Resolve student_id based on the triggering table
            CASE TG_TABLE_NAME
                WHEN 'enrollments' THEN
                    IF TG_OP = 'DELETE' THEN v_student_id := OLD.student_id;
                    ELSE v_student_id := NEW.student_id;
                    END IF;
                WHEN 'submissions' THEN
                    v_student_id := NEW.student_id;
                ELSE
                    RETURN NEW;
            END CASE;

            IF v_student_id IS NULL THEN
                RETURN NEW;
            END IF;

            INSERT INTO analytics.student_dashboard (id, student_id, total_courses, total_exams, total_submissions, total_graded_submissions, total_pending_submissions, missed_exams, upcoming_exams, created_at, updated_at)
            SELECT 
                gen_random_uuid(),
                v_student_id,
                (SELECT COUNT(*) FROM academic.enrollments WHERE student_id = v_student_id),
                (SELECT COUNT(DISTINCT e.id) FROM academic.exams e JOIN academic.enrollments en ON e.course_id = en.course_id WHERE en.student_id = v_student_id),
                (SELECT COUNT(*) FROM academic.submissions WHERE student_id = v_student_id),
                (SELECT COUNT(*) FROM academic.submissions WHERE student_id = v_student_id AND graded_at IS NOT NULL),
                (SELECT COUNT(*) FROM academic.submissions WHERE student_id = v_student_id AND graded_at IS NULL AND attempts_count > 0),
                0, -- missed_exams (requires complex logic)
                0,  -- upcoming_exams (requires complex logic)
                NOW(),
                NOW()
            ON CONFLICT (student_id) DO UPDATE SET
                total_courses = EXCLUDED.total_courses,
                total_exams = EXCLUDED.total_exams,
                total_submissions = EXCLUDED.total_submissions,
                total_graded_submissions = EXCLUDED.total_graded_submissions,
                total_pending_submissions = EXCLUDED.total_pending_submissions,
                updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create function to update admin dashboard
    op.execute("""
        CREATE OR REPLACE FUNCTION update_admin_dashboard()
        RETURNS TRIGGER AS $$
        DECLARE
            v_admin_id UUID;
            v_tenant_id UUID;
        BEGIN
            -- Get admin_id from context or use a default
            -- Note: users table doesn't have created_by column, so we find the first admin
            v_admin_id := (SELECT id FROM account.users WHERE role = 'admin' LIMIT 1);

            -- Resolve tenant_id based on the triggering table
            CASE TG_TABLE_NAME
                WHEN 'users' THEN
                    v_tenant_id := COALESCE(NEW.tenant_id, (SELECT tenant_id FROM account.users WHERE id = v_admin_id));
                WHEN 'courses' THEN
                    v_tenant_id := NEW.tenant_id;
                WHEN 'exams' THEN
                    v_tenant_id := NEW.tenant_id;
                WHEN 'submissions' THEN
                    v_tenant_id := (SELECT tenant_id FROM academic.exams WHERE id = NEW.exam_id);
                ELSE
                    v_tenant_id := (SELECT tenant_id FROM account.users WHERE id = v_admin_id);
            END CASE;

            IF v_admin_id IS NULL THEN
                RETURN NEW;
            END IF;
            
            INSERT INTO analytics.admin_dashboard (id, admin_id, total_users, total_lecturers, total_students, total_courses, total_exams, total_submissions, total_graded_submissions, total_pending_submissions, created_at, updated_at)
            SELECT 
                gen_random_uuid(),
                v_admin_id,
                (SELECT COUNT(*) FROM account.users WHERE tenant_id = v_tenant_id),
                (SELECT COUNT(*) FROM account.users WHERE tenant_id = v_tenant_id AND role = 'lecturer'),
                (SELECT COUNT(*) FROM account.users WHERE tenant_id = v_tenant_id AND role = 'student'),
                (SELECT COUNT(*) FROM academic.courses WHERE tenant_id = v_tenant_id),
                (SELECT COUNT(*) FROM academic.exams WHERE tenant_id = v_tenant_id),
                (SELECT COUNT(*) FROM academic.submissions s JOIN academic.exams e ON s.exam_id = e.id WHERE e.tenant_id = v_tenant_id),
                (SELECT COUNT(*) FROM academic.submissions s JOIN academic.exams e ON s.exam_id = e.id WHERE e.tenant_id = v_tenant_id AND s.graded_at IS NOT NULL),
                (SELECT COUNT(*) FROM academic.submissions s JOIN academic.exams e ON s.exam_id = e.id WHERE e.tenant_id = v_tenant_id AND s.graded_at IS NULL AND s.attempts_count > 0),
                NOW(),
                NOW()
            ON CONFLICT (admin_id) DO UPDATE SET
                total_users = EXCLUDED.total_users,
                total_lecturers = EXCLUDED.total_lecturers,
                total_students = EXCLUDED.total_students,
                total_courses = EXCLUDED.total_courses,
                total_exams = EXCLUDED.total_exams,
                total_submissions = EXCLUDED.total_submissions,
                total_graded_submissions = EXCLUDED.total_graded_submissions,
                total_pending_submissions = EXCLUDED.total_pending_submissions,
                updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers for Course table
    op.execute("""
        CREATE TRIGGER course_dashboard_trigger
        AFTER INSERT OR UPDATE OR DELETE ON academic.courses
        FOR EACH ROW EXECUTE FUNCTION update_lecturer_dashboard();
    """)

    op.execute("""
        CREATE TRIGGER course_admin_dashboard_trigger
        AFTER INSERT OR UPDATE OR DELETE ON academic.courses
        FOR EACH ROW EXECUTE FUNCTION update_admin_dashboard();
    """)

    # Create triggers for Exam table
    op.execute("""
        CREATE TRIGGER exam_dashboard_trigger
        AFTER INSERT OR UPDATE OR DELETE ON academic.exams
        FOR EACH ROW EXECUTE FUNCTION update_lecturer_dashboard();
    """)

    op.execute("""
        CREATE TRIGGER exam_admin_dashboard_trigger
        AFTER INSERT OR UPDATE OR DELETE ON academic.exams
        FOR EACH ROW EXECUTE FUNCTION update_admin_dashboard();
    """)

    # Create triggers for Enrollment table
    op.execute("""
        CREATE TRIGGER enrollment_lecturer_dashboard_trigger
        AFTER INSERT OR UPDATE OR DELETE ON academic.enrollments
        FOR EACH ROW EXECUTE FUNCTION update_lecturer_dashboard();
    """)

    op.execute("""
        CREATE TRIGGER enrollment_student_dashboard_trigger
        AFTER INSERT OR UPDATE OR DELETE ON academic.enrollments
        FOR EACH ROW EXECUTE FUNCTION update_student_dashboard();
    """)

    # Create triggers for Submission table
    op.execute("""
        CREATE TRIGGER submission_lecturer_dashboard_trigger
        AFTER INSERT OR UPDATE ON academic.submissions
        FOR EACH ROW EXECUTE FUNCTION update_lecturer_dashboard();
    """)

    op.execute("""
        CREATE TRIGGER submission_student_dashboard_trigger
        AFTER INSERT OR UPDATE ON academic.submissions
        FOR EACH ROW EXECUTE FUNCTION update_student_dashboard();
    """)

    op.execute("""
        CREATE TRIGGER submission_admin_dashboard_trigger
        AFTER INSERT OR UPDATE ON academic.submissions
        FOR EACH ROW EXECUTE FUNCTION update_admin_dashboard();
    """)

    # Create triggers for User table
    op.execute("""
        CREATE TRIGGER user_admin_dashboard_trigger
        AFTER INSERT OR UPDATE OR DELETE ON account.users
        FOR EACH ROW EXECUTE FUNCTION update_admin_dashboard();
    """)


def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS course_dashboard_trigger ON academic.courses")
    op.execute("DROP TRIGGER IF EXISTS course_admin_dashboard_trigger ON academic.courses")
    op.execute("DROP TRIGGER IF EXISTS exam_dashboard_trigger ON academic.exams")
    op.execute("DROP TRIGGER IF EXISTS exam_admin_dashboard_trigger ON academic.exams")
    op.execute("DROP TRIGGER IF EXISTS enrollment_lecturer_dashboard_trigger ON academic.enrollments")
    op.execute("DROP TRIGGER IF EXISTS enrollment_student_dashboard_trigger ON academic.enrollments")
    op.execute("DROP TRIGGER IF EXISTS submission_lecturer_dashboard_trigger ON academic.submissions")
    op.execute("DROP TRIGGER IF EXISTS submission_student_dashboard_trigger ON academic.submissions")
    op.execute("DROP TRIGGER IF EXISTS submission_admin_dashboard_trigger ON academic.submissions")
    op.execute("DROP TRIGGER IF EXISTS user_admin_dashboard_trigger ON account.users")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_lecturer_dashboard()")
    op.execute("DROP FUNCTION IF EXISTS update_student_dashboard()")
    op.execute("DROP FUNCTION IF EXISTS update_admin_dashboard()")
