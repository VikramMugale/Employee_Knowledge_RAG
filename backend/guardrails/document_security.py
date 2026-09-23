"""
Document Content Prompt Injection Defense module treating document text as untrusted data.
"""

import re
from typing import Optional, Dict, Any
from backend.guardrails.base import Guardrail, GuardrailResult


class DocumentContentGuardrail(Guardrail):
    """
    Treats retrieved document chunks as untrusted content, sanitizing and wrapping text
    to neutralize embedded malicious system overrides or prompt injection instructions inside document text.
    """

    UNTRUSTED_INSTRUCTION_PATTERNS = [
        r"(?i)system\s*:\s*ignore",
        r"(?i)override\s+system\s+prompt",
        r"(?i)do\s+not\s+follow\s+safety",
        r"(?i)forget\s+all\s+rules",
    ]

    async def validate(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        """Sanitize document text to ensure it remains passive context rather than LLM instructions."""
        sanitized = content
        for pattern in self.UNTRUSTED_INSTRUCTION_PATTERNS:
            sanitized = re.sub(pattern, "[NEUTRALIZED_UNTRUSTED_TEXT]", sanitized)

        return GuardrailResult(
            passed=True,
            risk_score=0.0,
            sanitized_content=sanitized
        )


document_content_guardrail = DocumentContentGuardrail()
