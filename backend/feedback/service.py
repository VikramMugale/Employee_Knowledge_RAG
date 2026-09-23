"""
Feedback collection service capturing ratings, comments, and converting negative traces into eval cases.
"""

import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from backend.config.logging import logger


class FeedbackSubmission(BaseModel):
    """User feedback submission payload."""
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    rating: int  # +1 (helpful) or -1 (not helpful)
    comment: Optional[str] = None
    trace_id: Optional[str] = None


class FeedbackItem(BaseModel):
    """Domain model for feedback records."""
    id: str
    user_id: str
    rating: int
    comment: Optional[str] = None
    trace_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackService:
    """Stores user feedback and provides bad-answer analysis dataset pipeline."""

    def __init__(self):
        self._feedback_store: List[FeedbackItem] = []

    async def submit_feedback(self, submission: FeedbackSubmission) -> FeedbackItem:
        """Store user feedback."""
        item = FeedbackItem(
            id=str(uuid.uuid4()),
            user_id=submission.user_id or "anonymous",
            rating=submission.rating,
            comment=submission.comment,
            trace_id=submission.trace_id,
        )
        self._feedback_store.append(item)
        logger.info(f"[FEEDBACK SUBMITTED] rating={item.rating} user={item.user_id} trace={item.trace_id}")
        return item

    async def get_analytics(self) -> Dict[str, Any]:
        """Calculate feedback metrics."""
        if not self._feedback_store:
            return {"total": 0, "positive": 0, "negative": 0, "satisfaction_rate": 0, "recent": []}

        total = len(self._feedback_store)
        positive = sum(1 for item in self._feedback_store if item.rating > 0)
        negative = total - positive

        recent = [
            {
                "rating": item.rating,
                "comment": item.comment,
                "trace_id": item.trace_id,
                "created_at": item.created_at.isoformat(),
            }
            for item in reversed(self._feedback_store[-8:])
        ]
        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "satisfaction_rate": round(positive / total, 4),
            "recent": recent,
        }


feedback_service = FeedbackService()
