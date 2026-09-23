"""
Lightweight query rewrite and intent classification.
"""

import re
from typing import List, Optional, Tuple
from backend.rag.models import QueryIntent

_POLICY_HINTS = (
    "leave", "pl", "cl", "wfh", "remote", "policy", "allowance", "stipend",
    "holiday", "carry", "privilege", "casual", "sick", "hybrid", "internet",
)
_ACTION_HINTS = ("approve", "submit", "apply for", "grant me", "change my")
_SENSITIVE_HINTS = ("salary", "compensation", "ssn", "password", "credentials")


def classify_intent(query: str) -> QueryIntent:
    lowered = query.lower()
    if any(hint in lowered for hint in _SENSITIVE_HINTS):
        return QueryIntent.SENSITIVE_REQUEST
    if any(hint in lowered for hint in _ACTION_HINTS):
        return QueryIntent.ACTION_REQUEST
    if any(hint in lowered for hint in _POLICY_HINTS):
        return QueryIntent.POLICY_QUESTION
    return QueryIntent.GENERAL_QUESTION


def rewrite_query(query: str, history: Optional[List[str]] = None) -> Tuple[str, QueryIntent]:
    intent = classify_intent(query)
    text = " ".join(query.split())
    history = history or []
    pronouns = re.search(r"\b(it|that|this|them|those)\b", text, re.IGNORECASE)
    if pronouns and history:
        last_user = history[-1]
        text = f"{text} (referring to: {last_user})"
    replacements = {
        r"\bPL\b": "Privilege Leave PL",
        r"\bCL\b": "Casual Leave CL",
        r"\bWFH\b": "work from home remote work WFH",
        r"\bcarry it\b": "carry forward unused leave",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return text, intent
