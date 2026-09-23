"""
Chat endpoints supporting standard response and Server-Sent Events (SSE) token streaming.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from backend.rag.models import RAGQuery, RAGResponse
from backend.rag.pipeline import rag_pipeline
from backend.auth.models import UserContext
from backend.api.dependencies import get_current_user_context


router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


@router.post("", response_model=RAGResponse)
async def chat_endpoint(
    req: ChatRequest,
    user_context: UserContext = Depends(get_current_user_context),
):
    """Standard non-streaming RAG question answering endpoint."""
    rag_query = RAGQuery(
        query_text=req.message,
        conversation_id=req.conversation_id,
        user_context=user_context,
    )
    return await rag_pipeline.execute(rag_query)


@router.post("/stream")
async def chat_stream_endpoint(
    req: ChatRequest,
    user_context: UserContext = Depends(get_current_user_context),
):
    """Real-time token streaming endpoint via Server-Sent Events (SSE)."""
    rag_query = RAGQuery(
        query_text=req.message,
        conversation_id=req.conversation_id,
        user_context=user_context,
    )
    return StreamingResponse(
        rag_pipeline.stream(rag_query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
