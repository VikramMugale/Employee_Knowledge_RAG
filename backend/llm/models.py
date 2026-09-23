"""
LLM abstraction provider protocols and request/response models.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """Standardized chat message payload."""
    role: str  # system, user, assistant
    content: str


class LLMRequest(BaseModel):
    """LLM completion request specifications."""
    messages: List[LLMMessage]
    temperature: float = 0.0
    max_tokens: Optional[int] = 1000
    model: str = "gemini-2.5-flash"
    stream: bool = False


class LLMResponse(BaseModel):
    """LLM generation response result."""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: Optional[str] = "stop"


class LLMProvider(ABC):
    """Abstract LLM Provider interface decoupled from concrete API SDKs."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate text completion from LLM."""
        pass

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream text completion tokens from LLM."""
        pass

    @abstractmethod
    async def embed(self, texts: List[str], model: str = "text-embedding-004") -> List[List[float]]:
        """Generate dense vector embeddings for texts."""
        pass
