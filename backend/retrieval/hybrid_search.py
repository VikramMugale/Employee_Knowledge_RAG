"""
Hybrid Retrieval engine combining Qdrant dense vector search, OpenSearch BM25, RRF fusion, and BGE reranking.
"""

import asyncio
from typing import List
from backend.retrieval.base import Retriever
from backend.retrieval.models import RetrievalQuery, CandidateChunk
from backend.retrieval.vector_search import vector_retriever
from backend.retrieval.keyword_search import keyword_retriever
from backend.retrieval.fusion import rrf_fusion
from backend.reranking.voyage_reranker import voyage_reranker
from backend.config.settings import settings
from backend.config.logging import logger


class HybridRetriever(Retriever):
    """
    Hybrid retriever running dense vector + BM25 keyword search in parallel,
    applying RRF fusion, and narrowing down via BGE cross-encoder reranking.
    """

    async def retrieve(self, query: RetrievalQuery) -> List[CandidateChunk]:
        """Execute parallel hybrid retrieval with RRF and reranking."""
        dense_task = asyncio.create_task(vector_retriever.retrieve(query))
        sparse_task = asyncio.create_task(keyword_retriever.retrieve(query))

        dense_candidates, sparse_candidates = await asyncio.gather(dense_task, sparse_task)

        fused_candidates = rrf_fusion.fuse(
            dense_candidates=dense_candidates,
            sparse_candidates=sparse_candidates,
            k=settings.retrieval.rrf_k,
            fusion_top_k=query.fusion_top_k,
        )

        rerank_result = await voyage_reranker.rerank(
            query=query.query_text,
            candidates=fused_candidates,
            top_k=settings.reranking.top_k,
        )

        logger.info(
            f"[HYBRID RETRIEVAL COMPLETE] Query: '{query.query_text}' | "
            f"Dense: {len(dense_candidates)} | Sparse: {len(sparse_candidates)} | "
            f"Fused: {len(fused_candidates)} | Reranked: {len(rerank_result.top_chunks)}"
        )

        return rerank_result.top_chunks


hybrid_retriever = HybridRetriever()
