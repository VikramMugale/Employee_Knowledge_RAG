"""
Abstract Retriever interface.
"""

from abc import ABC, abstractmethod
from typing import List
from backend.retrieval.models import RetrievalQuery, CandidateChunk


class Retriever(ABC):
    """Abstract interface protocol for vector, keyword, and hybrid retrievers."""

    @abstractmethod
    async def retrieve(self, query: RetrievalQuery) -> List[CandidateChunk]:
        """Execute candidate chunk search with user ACL metadata filtering."""
        pass
