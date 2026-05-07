from __future__ import annotations

from .base import GroqEngineBase
from .exam_extractor import ExamParser
from .answer_sheet_extractor import AnswerSheetParser
from .answer_grader import QuestionAnswerer
from .similarity_grader import SimilarityGrader

# Note: the in-process scheduler was removed in favor of the Kafka worker + scheduler.
# Keep engine exports for the core helpers; heavy scheduler logic was migrated
# into `backend/scheduler.py` which publishes events consumed by the worker.
__all__ = [
    "GroqEngineBase",
    "ExamParser",
    "AnswerSheetParser",
    "QuestionAnswerer",
    "SimilarityGrader",
]
