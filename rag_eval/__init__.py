"""End-to-end evaluation support for the physics-experiment RAG assistant."""

from .dataset import DatasetValidationError, load_questions, validate_questions
from .models import EvaluationQuestion, Prediction, RetrievedEvidence
from .scoring import build_report, score_prediction

__all__ = [
    "DatasetValidationError",
    "EvaluationQuestion",
    "Prediction",
    "RetrievedEvidence",
    "build_report",
    "load_questions",
    "score_prediction",
    "validate_questions",
]
