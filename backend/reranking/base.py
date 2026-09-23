"""
Abstract Reranker interface protocol and domain models.
"""

from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel
from backend.retrieval.models import CandidateChunk


class RerankResult(BaseModel):
    """Output payload from cross-encoder reranking."""
    top_chunks: List[CandidateChunk]
    reranker_model: str


class Reranker(ABC):
    """Abstract interface for reranking cross-encoder service."""

    @abstractmethod
    async def rerank(
        self, query: str, candidates: List[CandidateChunk], top_k: int = 8
    ) -> RerankResult:
        """Rerank candidate chunks using cross-encoder relevance scoring."""
        pass
