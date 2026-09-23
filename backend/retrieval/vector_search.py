"""
Qdrant dense vector search with in-memory fallback. OpenSearch is not required.
"""

from typing import List, Optional
from backend.retrieval.base import Retriever
from backend.retrieval.models import RetrievalQuery, CandidateChunk
from backend.retrieval.filters import acl_filter_builder
from backend.ingestion.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from backend.ingestion.models import Chunk, ChunkMetadata
from backend.config.settings import settings
from backend.config.logging import logger


def cosine_similarity(left: List[float], right: List[float]) -> float:
    """Cosine similarity over the overlapping prefix of two vectors."""
    size = min(len(left), len(right))
    if size == 0:
        return 0.0
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for index in range(size):
        left_val = left[index]
        right_val = right[index]
        dot += left_val * right_val
        left_norm += left_val * left_val
        right_norm += right_val * right_val
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / ((left_norm ** 0.5) * (right_norm ** 0.5))))


class QdrantVectorRetriever(Retriever):
    """Qdrant retriever with ACL payload filters and a local memory fallback."""

    def __init__(self):
        self.embedding_provider = GeminiEmbeddingProvider()
        self._memory_chunks: List[Chunk] = []
        self._client = None
        self.qdrant_ready = False

    def connect(self) -> bool:
        if not settings.uses_qdrant():
            logger.info("[QDRANT] QDRANT_URL not set; using in-memory vectors.")
            return False
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            url = (settings.qdrant_url or "").strip().strip('"').strip("'").rstrip("/")
            if url and "://" not in url:
                url = "https://" + url
            logger.info("[QDRANT] Connecting to %s", url)
            kwargs = {
                "url": url,
                "timeout": 60,
                "prefer_grpc": False,
            }
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key.strip()
            try:
                kwargs["check_compatibility"] = False
            except Exception:
                pass
            self._client = QdrantClient(**kwargs)
            existing = [item.name for item in self._client.get_collections().collections]
            if settings.qdrant_collection not in existing:
                self._client.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
            self._ensure_payload_indexes()
            self.qdrant_ready = True
            logger.info("[QDRANT] Connected. Collection=%s", settings.qdrant_collection)
            return True
        except Exception as exc:
            self._client = None
            self.qdrant_ready = False
            logger.error("[QDRANT] Unavailable, falling back to memory: %s", exc)
            return False

    def _collection_vector_size(self):
        try:
            info = self._client.get_collection(settings.qdrant_collection)
            vectors = info.config.params.vectors
            size = getattr(vectors, "size", None)
            return int(size) if size else None
        except Exception:
            return None

    def _align_collection_dim(self, dim):
        if not dim:
            return
        current = self._collection_vector_size()
        if current == dim:
            return
        from qdrant_client.http.models import Distance, VectorParams
        logger.warning("[QDRANT] Recreating collection for dim %s (was %s)", dim, current)
        try:
            self._client.delete_collection(settings.qdrant_collection)
        except Exception:
            pass
        self._client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        self._ensure_payload_indexes()
    def _ensure_payload_indexes(self) -> None:
        """Qdrant Cloud rejects payload filters until a keyword index exists."""
        try:
            from qdrant_client.http.models import PayloadSchemaType

            for field in ("access_level", "document_id"):
                try:
                    self._client.create_payload_index(
                        collection_name=settings.qdrant_collection,
                        field_name=field,
                        field_schema=PayloadSchemaType.KEYWORD,
                    )
                    logger.info("[QDRANT] Ensured payload index on %s", field)
                except Exception as exc:
                    logger.info("[QDRANT] Payload index %s: %s", field, exc)
        except Exception as exc:
            logger.warning("[QDRANT] Could not create payload indexes: %s", exc)

    def index_chunks(self, chunks: List[Chunk]):
        incoming_docs = {chunk.document_id for chunk in chunks}
        self._memory_chunks = [
            existing for existing in self._memory_chunks if existing.document_id not in incoming_docs
        ]
        self._memory_chunks.extend(chunks)
        logger.info("[VECTOR INDEX] Indexed %s chunks into memory.", len(chunks))
        if self.qdrant_ready and self._client:
            self._upsert_qdrant(chunks)

    def _upsert_qdrant(self, chunks: List[Chunk]) -> None:
        try:
            from qdrant_client.http.models import PointStruct

            points = []
            for chunk in chunks:
                if not chunk.embedding:
                    continue
                points.append(
                    PointStruct(
                        id=chunk.id,
                        vector=chunk.embedding,
                        payload={
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "content": chunk.content,
                            "document_title": chunk.metadata.document_title,
                            "document_version": chunk.metadata.document_version,
                            "section_title": chunk.metadata.section_title,
                            "content_hash": chunk.metadata.content_hash,
                            "access_level": chunk.metadata.access_level,
                            "allowed_roles": chunk.metadata.allowed_roles,
                            "paragraph_index": chunk.metadata.paragraph_index,
                        },
                    )
                )
            if points:
                self._align_collection_dim(len(points[0].vector))
                self._client.upsert(collection_name=settings.qdrant_collection, points=points)
                logger.info("[QDRANT] Upserted %s points.", len(points))
        except Exception as exc:
            logger.error("[QDRANT] Upsert failed: %s", exc)

    async def retrieve(self, query: RetrievalQuery) -> List[CandidateChunk]:
        query_vector = await self.embedding_provider.embed_query(query.query_text)
        if self.qdrant_ready and self._client:
            remote = self._search_qdrant(query, query_vector)
            if remote is not None:
                return remote
        return self._search_memory(query, query_vector)

    def _search_qdrant(self, query: RetrievalQuery, query_vector: List[float]) -> Optional[List[CandidateChunk]]:
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchAny

            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="access_level",
                        match=MatchAny(any=query.user_context.allowed_access_levels),
                    )
                ]
            )
            self._align_collection_dim(len(query_vector))
            logger.info("[QDRANT] Querying collection with query_points dim=%s", len(query_vector))
            try:
                response = self._client.query_points(
                    collection_name=settings.qdrant_collection,
                    query=query_vector,
                    query_filter=qdrant_filter,
                    limit=query.vector_top_k,
                    with_payload=True,
                )
            except Exception as exc:
                if "Index required" not in str(exc) and "400" not in str(exc):
                    raise
                logger.warning("[QDRANT] Filter index missing; querying without payload filter.")
                self._ensure_payload_indexes()
                response = self._client.query_points(
                    collection_name=settings.qdrant_collection,
                    query=query_vector,
                    limit=max(query.vector_top_k, 30),
                    with_payload=True,
                )
            results = getattr(response, "points", None)
            if results is None:
                results = response if isinstance(response, list) else []
            candidates: List[CandidateChunk] = []
            for hit in results:
                payload = hit.payload or {}
                metadata = ChunkMetadata(
                    document_id=str(payload.get("document_id") or ""),
                    document_title=str(payload.get("document_title") or "Policy"),
                    document_version=str(payload.get("document_version") or "2026.1"),
                    section_title=payload.get("section_title"),
                    paragraph_index=int(payload.get("paragraph_index") or 0),
                    content_hash=str(payload.get("content_hash") or ""),
                    access_level=str(payload.get("access_level") or "PUBLIC_INTERNAL"),
                    allowed_roles=list(payload.get("allowed_roles") or []),
                )
                if not acl_filter_builder.allows(query.user_context, metadata):
                    continue
                candidates.append(
                    CandidateChunk(
                        chunk_id=str(payload.get("chunk_id") or hit.id),
                        content=str(payload.get("content") or ""),
                        metadata=metadata,
                        dense_score=float(hit.score or 0.0),
                    )
                )
            logger.info("[QDRANT SEARCH] Retrieved %s candidates.", len(candidates))
            return candidates
        except Exception as exc:
            logger.error("[QDRANT] Search failed, using memory: %s", exc)
            return None

    def _search_memory(self, query: RetrievalQuery, query_vector: List[float]) -> List[CandidateChunk]:
        candidates: List[CandidateChunk] = []
        for chunk in self._memory_chunks:
            if not acl_filter_builder.allows(query.user_context, chunk.metadata):
                continue
            chunk_vector = chunk.embedding
            if not chunk_vector:
                continue
            candidates.append(
                CandidateChunk(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    dense_score=cosine_similarity(query_vector, chunk_vector),
                )
            )
        candidates.sort(key=lambda item: item.dense_score or 0.0, reverse=True)
        top_k = candidates[:query.vector_top_k]
        logger.info("[VECTOR SEARCH] Memory retrieved %s candidates.", len(top_k))
        return top_k


vector_retriever = QdrantVectorRetriever()
