"""
Abstract Guardrail interface protocol and result model.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class GuardrailResult(BaseModel):
    """Execution result from an input, output, or content guardrail check."""
    passed: bool
    risk_score: float = 0.0
    violation_type: Optional[str] = None
    reason: Optional[str] = None
    sanitized_content: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class Guardrail(ABC):
    """Abstract interface protocol for system guardrails."""

    @abstractmethod
    async def validate(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        """Validate input or output text content against security and policy rules."""
        pass
