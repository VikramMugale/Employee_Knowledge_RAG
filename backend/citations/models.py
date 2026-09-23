"""
Citation generation and validation models.
"""

from typing import List, Optional
from pydantic import BaseModel


class CitationVerification(BaseModel):
    """Citation claim-to-source validation result."""
    citation_id: str
    is_valid: bool
    confidence_score: float
    reason: Optional[str] = None
