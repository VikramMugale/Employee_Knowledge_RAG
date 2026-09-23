"""Document management and admin upload endpoints."""
import os
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from backend.ingestion.pipeline import ingestion_pipeline
from backend.auth.models import UserContext
from backend.api.dependencies import require_admin
from backend.retrieval.filters import acl_filter_builder
from backend.ingestion.models import ChunkMetadata
from backend.config.settings import ROOT_DIR

router = APIRouter(prefix="/documents", tags=["Documents"])
UPLOAD_DIR = os.path.join(ROOT_DIR, "data", "uploads")


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


@router.post("/upload")
async def upload_document(
    user_context: UserContext = Depends(require_admin),
    file: UploadFile = File(...),
    access_level: str = Form("PUBLIC_INTERNAL"),
    background: bool = Form(True),
):
    filename = os.path.basename(file.filename or "")
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in {"pdf", "md", "markdown", "txt"}:
        raise HTTPException(status_code=400, detail="Upload a PDF, Markdown, or text file.")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{filename}")
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file.")
    with open(dest, "wb") as handle:
        handle.write(payload)
    from backend.retrieval.vector_search import vector_retriever
    from backend.retrieval.keyword_search import keyword_retriever
    from backend.ingestion.jobs import ingestion_jobs
    if not vector_retriever.qdrant_ready:
        vector_retriever.connect()
    if not keyword_retriever.opensearch_ready:
        keyword_retriever.connect()
    if background:
        job = await ingestion_jobs.enqueue(dest)
        return {"status": "accepted", "job_id": job.id, "filename": filename, "access_level": access_level}
    document = await ingestion_pipeline.ingest_file(dest, access_level=access_level)
    return {"status": "success", "filename": filename, "document": document.title if document else None}


@router.post("/seed")
async def seed_documents(user_context: UserContext = Depends(require_admin)):
    return {"status": "disabled", "message": "Bundled seed policies were removed. Upload company PDFs from the Policies page."}


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
