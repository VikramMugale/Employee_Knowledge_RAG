"""
Abstract Document Parser interface.
"""

from abc import ABC, abstractmethod
from typing import List
from backend.ingestion.models import Chunk


class DocumentParser(ABC):
    """Abstract interface for structure-aware document parsing."""

    @abstractmethod
    async def parse(self, file_path: str, document_id: str) -> List[Chunk]:
        """Parse document into structure-aware chunks."""
        pass
