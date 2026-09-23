"""
Voyage / Atlas Embedding and Reranking API reranker.
Uses the Atlas model API key via VOYAGE_API_KEY.
"""

from typing import List
import httpx
from backend.reranking.base import Reranker, RerankResult
from backend.retrieval.models import CandidateChunk
from backend.config.settings import settings
from backend.config.logging import logger


class VoyageReranker(Reranker):
    """Calls POST /rerank on Atlas (ai.mongodb.com) or a custom Voyage base URL."""

    def __init__(self):
        self.model_name = settings.reranking.model_name
        self.api_key = settings.voyage_api_key
        self.base_url = settings.voyage_base_url.rstrip("/")

    async def rerank(
        self, query: str, candidates: List[CandidateChunk], top_k: int = 8
    ) -> RerankResult:
        if not candidates:
            return RerankResult(top_chunks=[], reranker_model=self.model_name)

        if not self.api_key:
            logger.warning("[RERANK] VOYAGE_API_KEY missing; using lexical fallback.")
            return self._lexical_fallback(query, candidates, top_k)

        documents = [_truncate(candidate.content) for candidate in candidates]
        url = f"{self.base_url}/rerank"
        payload = {
            "query": query,
            "documents": documents,
            "model": self.model_name,
            "top_k": min(top_k, len(documents)),
            "return_documents": False,
            "truncation": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
        except Exception as exc:
            logger.error("[RERANK] Voyage/Atlas rerank failed: %s. Using lexical fallback.", exc)
            return self._lexical_fallback(query, candidates, top_k)

        ranked = self._apply_scores(candidates, body)
        top_selected = ranked[:top_k]
        top_score = top_selected[0].reranker_score if top_selected else 0.0
        logger.info(
            "[RERANK] Voyage %s selected %s/%s (top_score=%.4f)",
            self.model_name,
            len(top_selected),
            len(candidates),
            top_score or 0.0,
        )
        return RerankResult(top_chunks=top_selected, reranker_model=self.model_name)

    def _apply_scores(self, candidates: List[CandidateChunk], body: dict) -> List[CandidateChunk]:
        rows = body.get("data") or body.get("results") or []
        scored: List[CandidateChunk] = []
        seen = set()
        for row in rows:
            index = row.get("index")
            score = row.get("relevance_score", row.get("score"))
            if index is None or score is None:
                continue
            if index < 0 or index >= len(candidates) or index in seen:
                continue
            seen.add(index)
            candidate = candidates[index]
            candidate.reranker_score = float(score)
            scored.append(candidate)
        scored.sort(key=lambda item: item.reranker_score or 0.0, reverse=True)
        if scored:
            return scored
        logger.warning("[RERANK] Unexpected Voyage payload keys=%s", list(body.keys()))
        return candidates

    def _lexical_fallback(
        self, query: str, candidates: List[CandidateChunk], top_k: int
    ) -> RerankResult:
        query_terms = set(query.lower().split())
        for candidate in candidates:
            text_terms = set(candidate.content.lower().split())
            overlap = query_terms.intersection(text_terms)
            base_score = candidate.fusion_score or 0.1
            boost = (len(overlap) / (len(query_terms) or 1)) * 0.5
            candidate.reranker_score = round(base_score + boost, 6)
        ranked = sorted(candidates, key=lambda item: item.reranker_score or 0.0, reverse=True)
        return RerankResult(top_chunks=ranked[:top_k], reranker_model="lexical-fallback")


def _truncate(text: str, limit: int = 4000) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit]


voyage_reranker = VoyageReranker()
