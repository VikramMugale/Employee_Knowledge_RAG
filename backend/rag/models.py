"""
RAG orchestration state, intent, and response domain models.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.auth.models import UserContext
from backend.retrieval.models import CandidateChunk


class QueryIntent(str, Enum):
    """Categorization of incoming user queries."""
    POLICY_QUESTION = "policy_question"
    GENERAL_QUESTION = "general_question"
    DOCUMENT_SEARCH = "document_search"
    UNSUPPORTED = "unsupported"
    ACTION_REQUEST = "action_request"
    SENSITIVE_REQUEST = "sensitive_request"


class CitationItem(BaseModel):
    """Citation reference item."""
    id: str
    document_title: str
    document_version: str
    section_title: Optional[str] = None
    snippet: str


class RAGQuery(BaseModel):
    """User input query request payload."""
    query_text: str
    conversation_id: Optional[str] = None
    user_context: UserContext


class RAGState(BaseModel):
    """LangGraph execution state representing pipeline context."""
    query_text: str
    rewritten_query: Optional[str] = None
    intent: QueryIntent = QueryIntent.POLICY_QUESTION
    user_context: UserContext
    retrieved_chunks: List[CandidateChunk] = Field(default_factory=list)
    reranked_chunks: List[CandidateChunk] = Field(default_factory=list)
    generated_answer: Optional[str] = None
    citations: List[CitationItem] = Field(default_factory=list)
    is_grounded: bool = True
    no_answer_flag: bool = False
    trace_id: Optional[str] = None


class RAGResponse(BaseModel):
    """Final response returned to caller/frontend API."""
    answer: str
    citations: List[CitationItem]
    no_answer_flag: bool
    conversation_id: Optional[str] = None
    trace_id: Optional[str] = None
