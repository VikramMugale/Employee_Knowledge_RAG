"""
Retrieval query and candidate chunk domain models.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.ingestion.models import ChunkMetadata
from backend.auth.models import UserContext


class RetrievalQuery(BaseModel):
    """Query configuration passed to vector and keyword retrievers."""
    query_text: str
    user_context: UserContext
    vector_top_k: int = 30
    keyword_top_k: int = 30
    fusion_top_k: int = 30
    metadata_filters: Dict[str, Any] = Field(default_factory=dict)


class CandidateChunk(BaseModel):
    """Scored candidate chunk returned during retrieval and fusion."""
    chunk_id: str
    content: str
    metadata: ChunkMetadata
    dense_score: Optional[float] = None
    bm25_score: Optional[float] = None
    fusion_score: Optional[float] = None
    reranker_score: Optional[float] = None


class RetrievalResult(BaseModel):
    """Result payload containing aggregated and scored candidate chunks."""
    query_text: str
    candidates: List[CandidateChunk]
    total_found: int
