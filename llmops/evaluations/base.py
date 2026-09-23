"""
Abstract Evaluator interface and evaluation case schemas.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class FailureCategory(str, Enum):
    """Categorization of RAG system failure modes."""
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    RERANKING_FAILURE = "RERANKING_FAILURE"
    CONTEXT_CONSTRUCTION_FAILURE = "CONTEXT_CONSTRUCTION_FAILURE"
    GENERATION_FAILURE = "GENERATION_FAILURE"
    GUARDRAIL_FAILURE = "GUARDRAIL_FAILURE"
    NONE = "NONE"


class EvaluationCase(BaseModel):
    """Golden dataset benchmark test case definition."""
    id: str
    question: str
    ground_truth_answer: str
    expected_document_id: str
    expected_section: Optional[str] = None
    category: str = "factual"
    is_out_of_scope: bool = False  # True for queries where no document supports answer


class EvaluationResult(BaseModel):
    """Result payload from evaluating a single query test case."""
    case_id: str
    question: str
    generated_answer: str
    faithfulness_score: float
    answer_relevance_score: float
    context_recall_score: float
    citation_accuracy: float
    no_answer_correct: bool
    failure_category: FailureCategory = FailureCategory.NONE
    details: Dict[str, Any] = Field(default_factory=dict)


class Evaluator(ABC):
    """Abstract interface protocol for evaluation framework implementations."""

    @abstractmethod
    async def evaluate_case(self, case: EvaluationCase, answer: str, context_chunks: List[str]) -> EvaluationResult:
        """Evaluate RAG pipeline output for a golden test case."""
        pass
