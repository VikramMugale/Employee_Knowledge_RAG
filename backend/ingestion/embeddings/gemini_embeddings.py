"""
Gemini embeddings via the current google.genai client, with a hash fallback.
"""

import hashlib
from typing import List
from backend.ingestion.embeddings.base import EmbeddingProvider
from backend.config.settings import settings
from backend.config.logging import logger


def _hash_embedding(text: str, dim: int = 768) -> List[float]:
    digest = hashlib.sha256((text or "").encode("utf-8")).digest()
    seed = sum(digest) / len(digest)
    return [(seed + (index * 0.001)) % 1.0 for index in range(dim)]


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.embedding_model or "gemini-embedding-001"
        self.active = bool(self.api_key)
        self._new_client = None
        self._old = None
        if self.active:
            try:
                from google import genai
                self._new_client = genai.Client(api_key=self.api_key)
            except Exception:
                try:
                    import google.generativeai as genai_old
                    genai_old.configure(api_key=self.api_key)
                    self._old = genai_old
                except Exception:
                    self.active = False
        if not self.active:
            if settings.environment == "production" and not settings.allow_hash_embeddings:
                logger.error("[EMBEDDINGS] Gemini unavailable; hash fallback disabled in production.")
            else:
                logger.warning("[EMBEDDINGS] Gemini unavailable; using hash vectors (dev only).")

    def _embed_one(self, text: str, task_type: str) -> List[float]:
        models = [self.model, "gemini-embedding-001", "text-embedding-004"]
        last_error = None
        target_dim = int(settings.embedding_dimension or 768)
        if self._new_client is not None:
            for model_name in models:
                try:
                    try:
                        result = self._new_client.models.embed_content(
                            model=model_name,
                            contents=text,
                            config={"output_dimensionality": target_dim},
                        )
                    except TypeError:
                        result = self._new_client.models.embed_content(model=model_name, contents=text)
                    vectors = getattr(result, "embeddings", None) or []
                    if vectors:
                        values = getattr(vectors[0], "values", None) or vectors[0]
                        vector = list(values)
                        if len(vector) > target_dim:
                            return vector[:target_dim]
                        return vector
                    embedding = getattr(result, "embedding", None)
                    if embedding is not None:
                        values = getattr(embedding, "values", embedding)
                        vector = list(values)
                        if len(vector) > target_dim:
                            return vector[:target_dim]
                        return vector
                except Exception as exc:
                    last_error = exc
        if self._old is not None:
            for model_name in models:
                for model_id in (model_name, f"models/{model_name}"):
                    try:
                        result = self._old.embed_content(model=model_id, content=text, task_type=task_type)
                        vector = result["embedding"] if isinstance(result, dict) else result.embedding
                        return list(vector)
                    except Exception as exc:
                        last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("No Gemini embedding client")

    def _fallback_or_fail(self, reason: str) -> None:
        if settings.environment == "production" and not settings.allow_hash_embeddings:
            raise RuntimeError(f"Embedding provider unavailable in production: {reason}")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.active:
            try:
                return [self._embed_one(text, "retrieval_document") for text in texts]
            except Exception as exc:
                logger.error("[EMBEDDING API ERROR] Gemini Embedding failed: %s.", exc)
                self._fallback_or_fail(str(exc))
        else:
            self._fallback_or_fail("Gemini client not configured")
        return [_hash_embedding(text) for text in texts]

    async def embed_query(self, query: str) -> List[float]:
        if self.active:
            try:
                return self._embed_one(query, "retrieval_query")
            except Exception as exc:
                logger.error("[EMBEDDING API ERROR] Gemini Query Embedding failed: %s.", exc)
                self._fallback_or_fail(str(exc))
        else:
            self._fallback_or_fail("Gemini client not configured")
        return _hash_embedding(query)
