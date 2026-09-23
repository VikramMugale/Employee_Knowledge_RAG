"""
Prompt injection attack detection guardrail.
"""

import re
from typing import Optional, Dict, Any
from backend.guardrails.base import Guardrail, GuardrailResult


class PromptInjectionGuardrail(Guardrail):
    """Detects direct prompt injection attacks, jailbreak attempts, and system prompt extraction."""

    INJECTION_PATTERNS = [
        r"(?i)ignore\s+previous\s+instructions",
        r"(?i)reveal\s+(system|your)\s+prompt",
        r"(?i)override\s+company\s+policy",
        r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
        r"(?i)jailbreak",
        r"(?i)act\s+as\s+an\s+unrestricted"
    ]

    async def validate(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        """Scan content for prompt injection patterns."""
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, content):
                return GuardrailResult(
                    passed=False,
                    risk_score=0.95,
                    violation_type="PROMPT_INJECTION",
                    reason="Prompt injection or jailbreak attempt detected."
                )

        return GuardrailResult(passed=True, risk_score=0.0)


prompt_injection_guardrail = PromptInjectionGuardrail()
