"""
OpenSearch BM25 keyword retriever with in-memory fallback.
"""

import re
from typing import List, Optional
from backend.retrieval.base import Retriever
from backend.retrieval.models import RetrievalQuery, CandidateChunk
from backend.retrieval.filters import acl_filter_builder
from backend.ingestion.models import Chunk, ChunkMetadata
from backend.config.settings import settings
from backend.config.logging import logger


class OpenSearchKeywordRetriever(Retriever):
    """BM25 lexical retriever backed by OpenSearch when configured."""

    def __init__(self):
        self._memory_chunks: List[Chunk] = []
        self._client = None
        self.opensearch_ready = False

    def connect(self) -> bool:
        if not settings.uses_opensearch():
            logger.info("[OPENSEARCH] OPENSEARCH_URL not set; using in-memory keyword search.")
            return False
        try:
            from opensearchpy import OpenSearch

            kwargs = {
                "hosts": [settings.opensearch_url],
                "use_ssl": settings.opensearch_url.startswith("https://"),
                "verify_certs": settings.opensearch_url.startswith("https://"),
                "ssl_show_warn": False,
            }
            if settings.opensearch_user:
                kwargs["http_auth"] = (settings.opensearch_user, settings.opensearch_password)
            self._client = OpenSearch(**kwargs)
            if not self._client.indices.exists(index=settings.opensearch_index):
                self._client.indices.create(
                    index=settings.opensearch_index,
                    body={
                        "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
                        "mappings": {
                            "properties": {
                                "content": {"type": "text"},
                                "access_level": {"type": "keyword"},
                                "allowed_roles": {"type": "keyword"},
                                "document_id": {"type": "keyword"},
                                "chunk_id": {"type": "keyword"},
                                "document_title": {"type": "text"},
                                "document_version": {"type": "keyword"},
                                "section_title": {"type": "text"},
                                "content_hash": {"type": "keyword"},
                                "paragraph_index": {"type": "integer"},
                            }
                        },
                    },
                )
            self.opensearch_ready = True
            logger.info("[OPENSEARCH] Connected. Index=%s", settings.opensearch_index)
            return True
        except Exception as exc:
            self._client = None
            self.opensearch_ready = False
            logger.error("[OPENSEARCH] Unavailable, falling back to memory: %s", exc)
            return False

    def index_chunks(self, chunks: List[Chunk]):
        incoming_docs = {chunk.document_id for chunk in chunks}
        self._memory_chunks = [
            existing for existing in self._memory_chunks if existing.document_id not in incoming_docs
        ]
        self._memory_chunks.extend(chunks)
        logger.info("[KEYWORD INDEX] Indexed %s chunks into memory.", len(chunks))
        if self.opensearch_ready and self._client:
            self._upsert_opensearch(chunks)

    def _upsert_opensearch(self, chunks: List[Chunk]) -> None:
        try:
            from opensearchpy.helpers import bulk

            actions = []
            for chunk in chunks:
                actions.append(
                    {
                        "_op_type": "index",
                        "_index": settings.opensearch_index,
                        "_id": chunk.id,
                        "_source": {
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
                    }
                )
            if actions:
                bulk(self._client, actions, refresh=True)
                logger.info("[OPENSEARCH] Upserted %s documents.", len(actions))
        except Exception as exc:
            logger.error("[OPENSEARCH] Upsert failed: %s", exc)

    async def retrieve(self, query: RetrievalQuery) -> List[CandidateChunk]:
        if self.opensearch_ready and self._client:
            remote = self._search_opensearch(query)
            if remote is not None:
                return remote
        return self._search_memory(query)

    def _search_opensearch(self, query: RetrievalQuery) -> Optional[List[CandidateChunk]]:
        try:
            body = {
                "size": query.keyword_top_k,
                "query": {
                    "bool": {
                        "must": {
                            "multi_match": {
                                "query": query.query_text,
                                "fields": ["content", "document_title", "section_title"],
                            }
                        },
                        "filter": {
                            "terms": {"access_level": query.user_context.allowed_access_levels}
                        },
                    }
                },
            }
            response = self._client.search(index=settings.opensearch_index, body=body)
            hits = response.get("hits", {}).get("hits", [])
            candidates: List[CandidateChunk] = []
            for hit in hits:
                source = hit.get("_source") or {}
                metadata = ChunkMetadata(
                    document_id=str(source.get("document_id") or ""),
                    document_title=str(source.get("document_title") or "Policy"),
                    document_version=str(source.get("document_version") or "2026.1"),
                    section_title=source.get("section_title"),
                    paragraph_index=int(source.get("paragraph_index") or 0),
                    content_hash=str(source.get("content_hash") or ""),
                    access_level=str(source.get("access_level") or "PUBLIC_INTERNAL"),
                    allowed_roles=list(source.get("allowed_roles") or []),
                )
                if not acl_filter_builder.allows(query.user_context, metadata):
                    continue
                candidates.append(
                    CandidateChunk(
                        chunk_id=str(source.get("chunk_id") or hit.get("_id")),
                        content=str(source.get("content") or ""),
                        metadata=metadata,
                        bm25_score=float(hit.get("_score") or 0.0),
                    )
                )
            logger.info("[OPENSEARCH SEARCH] Retrieved %s candidates.", len(candidates))
            return candidates
        except Exception as exc:
            logger.error("[OPENSEARCH] Search failed, using memory: %s", exc)
            return None

    def _search_memory(self, query: RetrievalQuery) -> List[CandidateChunk]:
        query_terms = set(re.findall(r"\w+", query.query_text.lower()))
        candidates: List[CandidateChunk] = []
        for chunk in self._memory_chunks:
            if not acl_filter_builder.allows(query.user_context, chunk.metadata):
                continue
            chunk_terms = set(re.findall(r"\w+", chunk.content.lower()))
            overlap = query_terms.intersection(chunk_terms)
            if not overlap:
                continue
            candidates.append(
                CandidateChunk(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    bm25_score=len(overlap) / (len(query_terms) or 1.0),
                )
            )
        candidates.sort(key=lambda item: item.bm25_score or 0.0, reverse=True)
        top_k = candidates[:query.keyword_top_k]
        logger.info("[KEYWORD SEARCH] Memory BM25 retrieved %s candidates.", len(top_k))
        return top_k


keyword_retriever = OpenSearchKeywordRetriever()
