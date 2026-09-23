"""
Abstract CitationGenerator interface.
"""

from abc import ABC, abstractmethod
from typing import List
from backend.rag.models import CitationItem
from backend.retrieval.models import CandidateChunk


class CitationGenerator(ABC):
    """Abstract interface for source citation extraction and verification."""

    @abstractmethod
    async def generate_citations(
        self, answer: str, source_chunks: List[CandidateChunk]
    ) -> List[CitationItem]:
        """Generate verified citation items referencing original document sections."""
        pass
