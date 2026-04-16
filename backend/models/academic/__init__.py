"""Academic models package.

Expose common academic models:
```
from backend.models.academic import Course, Exam, Submission, SubmissionAttempt
```
"""

from .course import Course
from .exam import Exam
from .submission import Submission, SubmissionAttempt

__all__ = ["Course", "Exam", "Submission", "SubmissionAttempt"]
