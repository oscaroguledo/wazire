"""
Import all models to ensure they're available before SQLAlchemy configures mappers.
This prevents circular dependency errors when models reference each other.
"""

# Import account models first (base models)
from models.account.users import User
from models.account.tenant import Tenant

# Import billing models (depend on account models)
from models.billings.invoice import Invoice
from models.billings.usage import CurrentUsage
from models.billings.paymentmethod import PaymentMethod

# Import academic models (depend on account models)
from models.academic.course import Course
from models.academic.enrollment import Enrollment
from models.academic.exam import Exam
from models.academic.question import Question, Answer, QuestionExams
from models.academic.submission import Submission, SubmissionAttempt
from models.academic.student_answer import StudentAnswer

# Import analytics models (depend on account models)
from models.analytics.dashboard import LecturerDashboard, AdminDashboard, StudentDashboard

__all__ = [
    'User',
    'Tenant',
    'Invoice',
    'CurrentUsage',
    'PaymentMethod',
    'Course',
    'Enrollment',
    'Exam',
    'Question',
    'Answer',
    'QuestionExams',
    'Submission',
    'SubmissionAttempt',
    'StudentAnswer',
    'LecturerDashboard',
    'AdminDashboard',
    'StudentDashboard',
]
