"""
Admin LLMOps evaluation and analytics endpoints.
"""

from fastapi import APIRouter, Depends
from backend.auth.models import UserContext
from backend.api.dependencies import require_admin
from backend.config.settings import settings
from backend.feedback.service import feedback_service
from backend.ingestion.pipeline import ingestion_pipeline
from backend.retrieval.vector_search import vector_retriever
from backend.retrieval.keyword_search import keyword_retriever
from backend.db.session import engine
from observability.tracing.telemetry import telemetry_tracer
from llmops.evaluations.eval_runner import baseline_evaluations
from llmops.regression.regression_suite import regression_gate

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def admin_dashboard(admin_ctx: UserContext = Depends(require_admin)):
    """Aggregated admin workspace: index, services, and feedback."""
    documents = list(ingestion_pipeline.documents_registry.values())
    analytics = await feedback_service.get_analytics()
    return {
        "documents": {
            "count": len(documents),
            "items": [
                {
                    "id": document.id,
                    "title": document.title,
                    "access_level": document.access_level,
                    "lifecycle_state": document.lifecycle_state.value
                    if hasattr(document.lifecycle_state, "value")
                    else document.lifecycle_state,
                    "version": document.version,
                    "owner": document.owner,
                    "chunks": len(ingestion_pipeline.chunks_registry.get(document.id, [])),
                }
                for document in documents
            ],
        },
        "index": {
            "vector_memory": len(getattr(vector_retriever, "_memory_chunks", [])),
            "keyword_memory": len(getattr(keyword_retriever, "_memory_chunks", [])),
            "qdrant": "connected" if getattr(vector_retriever, "qdrant_ready", False) else "fallback",
            "opensearch": "connected" if getattr(keyword_retriever, "opensearch_ready", False) else "fallback",
        },
        "services": {
            "gemini": "configured" if settings.gemini_api_key else "mock",
            "voyage": "configured" if settings.voyage_api_key else "fallback",
            "postgres": "connected" if engine is not None else "off",
            "langfuse": "connected" if telemetry_tracer.ready else "off",
        },
        "feedback": analytics,
    }


@router.get("/evaluations/run")
async def run_evaluations_endpoint(admin_ctx: UserContext = Depends(require_admin)):
    """Run LLMOps benchmark evaluation suite."""
    return await baseline_evaluations.run_suite()


@router.get("/evaluations/gate")
async def run_quality_gate_endpoint(admin_ctx: UserContext = Depends(require_admin)):
    """Check regression quality gate status."""
    passed = await regression_gate.run_quality_gate()
    return {"status": "PASSED" if passed else "FAILED", "gate_passed": passed}
