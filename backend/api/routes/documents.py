"""
Document management and ingestion endpoints.
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.ingestion.pipeline import ingestion_pipeline
from backend.auth.models import UserContext
from backend.api.dependencies import require_admin
from backend.retrieval.filters import acl_filter_builder
from backend.ingestion.models import ChunkMetadata


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("")
async def list_documents(user_context: UserContext = Depends(require_admin)):
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


class IngestRequest(BaseModel):
    file_path: str
    background: bool = True


@router.post("", status_code=202)
async def ingest_document(req: IngestRequest, user_context: UserContext = Depends(require_admin)):
    from backend.ingestion.jobs import ingestion_jobs

    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    if req.background:
        job = await ingestion_jobs.enqueue(req.file_path)
        return {"status": "accepted", "job_id": job.id}
    document = await ingestion_pipeline.ingest_file(req.file_path)
    return {"status": "success", "document": document.title if document else None}


@router.get("/jobs/{job_id}")
async def get_ingest_job(job_id: str, user_context: UserContext = Depends(require_admin)):
    from backend.ingestion.jobs import ingestion_jobs

    job = ingestion_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
