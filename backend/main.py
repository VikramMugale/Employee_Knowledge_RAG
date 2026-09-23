"""
FastAPI Main Application Entry Point with Hardened CORS and Routes.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.router import api_router
from backend.api.routes.health import router as health_router
from backend.config.settings import settings
from backend.config.logging import logger
from backend.api.rate_limit import InMemoryRateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"[{settings.app_name}] Application starting in '{settings.environment}' environment."
    )
    from backend.db.session import init_database
    from backend.retrieval.vector_search import vector_retriever
    from backend.retrieval.keyword_search import keyword_retriever
    from observability.tracing.telemetry import telemetry_tracer

    await init_database()
    vector_retriever.connect()
    keyword_retriever.connect()
    telemetry_tracer.connect()
    from backend.ingestion.jobs import ingestion_jobs
    ingestion_jobs.start()
    if not settings.uses_redis():
        logger.info("[CACHE] Redis not configured and not used.")
    yield
    logger.info(f"[{settings.app_name}] Application shutting down.")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(InMemoryRateLimiter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "User-Agent"],
)

app.include_router(health_router)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
