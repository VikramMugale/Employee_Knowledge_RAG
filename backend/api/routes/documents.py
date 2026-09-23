"""
Document management and ingestion endpoints.
"""

import os
from fastapi import APIRouter, Depends
from backend.ingestion.pipeline import ingestion_pipeline
from backend.auth.models import UserContext
from backend.api.dependencies import require_admin
from backend.retrieval.filters import acl_filter_builder
from backend.ingestion.models import ChunkMetadata


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("")
async def list_documents(user_context: UserContext = Depends(require_admin)):
    """List ingested documents visible to the caller."""
    visible = []
    for document in ingestion_pipeline.documents_registry.values():
        metadata = ChunkMetadata(
            document_id=document.id,
            document_title=document.title,
            document_version=document.version,
            content_hash=document.content_hash,
            access_level=document.access_level,
        )
        if acl_filter_builder.allows(user_context, metadata):
            visible.append(document)
    return visible


@router.post("/seed")
async def seed_documents(user_context: UserContext = Depends(require_admin)):
    """Trigger ingestion of local seed policies from data/seed/policies/."""
    from backend.config.settings import ROOT_DIR

    seed_dir = os.path.abspath(os.path.join(ROOT_DIR, "data", "seed", "policies"))
    if not os.path.exists(seed_dir):
        return {"status": "error", "message": f"Seed directory not found at {seed_dir}"}

    from backend.retrieval.vector_search import vector_retriever
    from backend.retrieval.keyword_search import keyword_retriever

    if not vector_retriever.qdrant_ready:
        vector_retriever.connect()
    if not keyword_retriever.opensearch_ready:
        keyword_retriever.connect()

    ingested = await ingestion_pipeline.ingest_directory(seed_dir)
    return {
        "status": "success",
        "ingested_count": len(ingested),
        "documents": [document.title for document in ingested],
        "qdrant": "connected" if vector_retriever.qdrant_ready else "fallback",
        "opensearch": "connected" if keyword_retriever.opensearch_ready else "fallback",
    }
