"""
Health checks that report configured services honestly.
Redis is optional and unused. OpenSearch is used for keyword search when configured.
"""

from fastapi import APIRouter
from backend.retrieval.vector_search import vector_retriever
from backend.retrieval.keyword_search import keyword_retriever
from backend.config.settings import settings
from observability.tracing.telemetry import telemetry_tracer
from backend.db.session import engine

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@router.get("/ready")
async def readiness_check():
    vector_count = len(getattr(vector_retriever, "_memory_chunks", []))
    keyword_count = len(getattr(keyword_retriever, "_memory_chunks", []))
    return {
        "status": "ready",
        "dependencies": {
            "gemini": "configured" if settings.gemini_api_key else "mock_fallback",
            "postgres": "configured" if engine is not None else ("missing_url" if not settings.uses_postgres() else "unavailable"),
            "qdrant": "connected" if vector_retriever.qdrant_ready else ("missing_url" if not settings.uses_qdrant() else "unavailable"),
            "langfuse": "connected" if telemetry_tracer.ready else ("missing_keys" if not settings.uses_langfuse() else "unavailable"),
            "keyword_index": "opensearch" if keyword_retriever.opensearch_ready else "in_memory",
            "opensearch": "connected" if keyword_retriever.opensearch_ready else ("missing_url" if not settings.uses_opensearch() else "unavailable"),
            "redis": "not_used",
        },
        "indexed_chunks": {"vector_memory": vector_count, "keyword": keyword_count},
    }


@router.get("/live")
async def liveness_check():
    return {"status": "alive"}
