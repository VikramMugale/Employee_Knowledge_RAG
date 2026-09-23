"""
Abstract EmbeddingProvider interface.
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Abstract interface for text vector embedding generation."""

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate dense vector representations for a list of string texts."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate dense vector representation for a user search query."""
        pass
