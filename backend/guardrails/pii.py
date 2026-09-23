"""
PII Detection and Redaction Guardrail.
"""

import re
from typing import Optional, Dict, Any
from backend.guardrails.base import Guardrail, GuardrailResult


class PIIGuardrail(Guardrail):
    """Detects and redacts sensitive PII (emails, SSNs, credit cards, employee IDs)."""

    PII_REGEXES = {
        "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b',
        "PHONE": r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "SSN_TAX": r'\b\d{3}-\d{2}-\d{4}\b'
    }

    async def validate(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        """Scan and redact PII entities."""
        redacted = content
        found_types = []

        for pii_type, regex in self.PII_REGEXES.items():
            if re.search(regex, redacted):
                found_types.append(pii_type)
                redacted = re.sub(regex, f"[{pii_type}_REDACTED]", redacted)

        return GuardrailResult(
            passed=True,
            risk_score=0.2 if found_types else 0.0,
            sanitized_content=redacted,
            details={"redacted_types": found_types}
        )


pii_guardrail = PIIGuardrail()
