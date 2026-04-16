from __future__ import annotations

from .base import GroqEngineBase
from .exam_extractor import ExamParser
from .answer_sheet_extractor import AnswerSheetParser
from .answer_grader import QuestionAnswerer
from .similarity_grader import SimilarityGrader

# Note: the in-process scheduler was removed in favor of Celery + Celery Beat.
# Keep engine exports for the core helpers; heavy scheduler logic was migrated
# into Celery tasks (see `backend/tasks/scheduler_tasks.py`).
__all__ = [
    "GroqEngineBase",
    "ExamParser",
    "AnswerSheetParser",
    "QuestionAnswerer",
    "SimilarityGrader",
]
