"""
Feedback submission endpoints.
"""

from fastapi import APIRouter, Depends
from backend.feedback.service import feedback_service, FeedbackSubmission, FeedbackItem
from backend.auth.models import UserContext
from backend.api.dependencies import get_current_user_context, require_admin

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackItem)
async def submit_feedback_endpoint(
    submission: FeedbackSubmission,
    user_context: UserContext = Depends(get_current_user_context),
):
    """Submit user feedback rating and comments."""
    submission.user_id = user_context.user_id
    return await feedback_service.submit_feedback(submission)


@router.get("/analytics")
async def get_feedback_analytics(user_context: UserContext = Depends(require_admin)):
    """Retrieve aggregated feedback satisfaction analytics."""
    return await feedback_service.get_analytics()
