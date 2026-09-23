"""
Application settings and configuration management.
Loads environment variables from a project-root .env file when present.
"""

import os
from typing import List
from pydantic import BaseModel, Field

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_FILE_PATH = os.path.join(ROOT_DIR, ".env")


def _load_env_file(path: str) -> None:
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)


_load_env_file(ENV_FILE_PATH)
_load_env_file(os.path.join(os.getcwd(), ".env"))


def neon_async_database_url(url: str) -> str:
    raw = (url or "").strip()
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://") and "+asyncpg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "?" in raw:
        base, query = raw.split("?", 1)
        kept = [
            part
            for part in query.split("&")
            if part
            and not part.lower().startswith("sslmode=")
            and not part.lower().startswith("channel_binding=")
        ]
        raw = base + (("?" + "&".join(kept)) if kept else "")
    return raw


class RetrievalSettings(BaseModel):
    vector_top_k: int = 30
    keyword_top_k: int = 30
    fusion_top_k: int = 30
    rrf_k: int = 60


class RerankSettings(BaseModel):
    top_k: int = Field(default_factory=lambda: int(os.getenv("RERANK_TOP_K", "8")))
    model_name: str = Field(default_factory=lambda: os.getenv("RERANK_MODEL", "rerank-2.5"))


class Settings(BaseModel):
    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "Employee Knowledge RAG Platform"))
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    secret_key: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "development-secret-key-at-least-32-chars-long"))

    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", ""))

    qdrant_url: str = Field(default_factory=lambda: os.getenv("QDRANT_URL", ""))
    qdrant_api_key: str = Field(default_factory=lambda: os.getenv("QDRANT_API_KEY", ""))
    qdrant_collection: str = Field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "employee_rag_chunks"))
    opensearch_url: str = Field(default_factory=lambda: os.getenv("OPENSEARCH_URL", ""))
    opensearch_user: str = Field(default_factory=lambda: os.getenv("OPENSEARCH_USER") or os.getenv("OPENSEARCH_USERNAME", ""))
    opensearch_password: str = Field(default_factory=lambda: os.getenv("OPENSEARCH_PASSWORD", ""))
    opensearch_index: str = Field(default_factory=lambda: os.getenv("OPENSEARCH_INDEX", "employee_rag_chunks"))

    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    embedding_model: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-004"))
    embedding_dimension: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_DIMENSION", "768")))

    voyage_api_key: str = Field(default_factory=lambda: os.getenv("VOYAGE_API_KEY", ""))
    voyage_base_url: str = Field(default_factory=lambda: os.getenv("VOYAGE_BASE_URL", "https://ai.mongodb.com/v1"))

    langfuse_public_key: str = Field(default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY", ""))
    langfuse_secret_key: str = Field(default_factory=lambda: os.getenv("LANGFUSE_SECRET_KEY", ""))
    langfuse_host: str = Field(default_factory=lambda: os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"))
    langfuse_base_url: str = Field(default_factory=lambda: os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))

    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY", "development-secret-key-at-least-32-chars-long"))
    jwt_algorithm: str = Field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    jwt_expire_minutes: int = Field(default_factory=lambda: int(os.getenv("JWT_EXPIRE_MINUTES", "480")))
    jwt_issuer: str = Field(default_factory=lambda: os.getenv("JWT_ISSUER", "employee-rag"))
    jwt_audience: str = Field(default_factory=lambda: os.getenv("JWT_AUDIENCE", "employee-rag-api"))

    cors_origins: List[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ]
    )

    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    reranking: RerankSettings = Field(default_factory=RerankSettings)
    chunk_max_tokens: int = Field(default_factory=lambda: int(os.getenv("CHUNK_MAX_TOKENS", "550")))
    chunk_overlap_tokens: int = Field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP_TOKENS", "80")))
    allow_hash_embeddings: bool = Field(
        default_factory=lambda: os.getenv("ALLOW_HASH_EMBEDDINGS", "true").lower() == "true"
    )
    rate_limit_per_minute: int = Field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")))
    active_versions_only: bool = Field(
        default_factory=lambda: os.getenv("ACTIVE_VERSIONS_ONLY", "true").lower() == "true"
    )

    def uses_postgres(self) -> bool:
        return bool(self.database_url)

    def uses_qdrant(self) -> bool:
        return bool(self.qdrant_url)

    def uses_langfuse(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    def uses_opensearch(self) -> bool:
        return bool(self.opensearch_url)

    def uses_redis(self) -> bool:
        return bool(self.redis_url)

    def async_database_url(self) -> str:
        return neon_async_database_url(self.database_url)


settings = Settings()
