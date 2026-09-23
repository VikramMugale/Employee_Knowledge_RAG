"""Retrieval metrics and staged retrieval experiments (no Redis)."""
from typing import Dict, List, Sequence
import math
import time


def recall_at_k(relevant: Sequence[str], ranked: Sequence[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & set(relevant)) / len(set(relevant))


def precision_at_k(relevant: Sequence[str], ranked: Sequence[str], k: int) -> float:
    top = ranked[:k]
    if not top:
        return 0.0
    return len(set(top) & set(relevant)) / len(top)


def mrr_at_k(relevant: Sequence[str], ranked: Sequence[str], k: int = 10) -> float:
    wanted = set(relevant)
    for index, item in enumerate(ranked[:k], start=1):
        if item in wanted:
            return 1.0 / index
    return 0.0


def ndcg_at_k(relevant: Sequence[str], ranked: Sequence[str], k: int = 10) -> float:
    wanted = set(relevant)
    dcg = sum(1.0 / math.log2(index + 1) for index, item in enumerate(ranked[:k], start=1) if item in wanted)
    ideal_hits = min(len(wanted), k)
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def hit_rate(relevant: Sequence[str], ranked: Sequence[str], k: int = 10) -> float:
    return 1.0 if set(ranked[:k]) & set(relevant) else 0.0


def score_ranking(relevant: Sequence[str], ranked: Sequence[str]) -> Dict[str, float]:
    return {
        "recall@5": round(recall_at_k(relevant, ranked, 5), 4),
        "recall@10": round(recall_at_k(relevant, ranked, 10), 4),
        "precision@5": round(precision_at_k(relevant, ranked, 5), 4),
        "mrr@10": round(mrr_at_k(relevant, ranked, 10), 4),
        "ndcg@10": round(ndcg_at_k(relevant, ranked, 10), 4),
        "hit_rate@10": round(hit_rate(relevant, ranked, 10), 4),
    }


async def run_retrieval_experiments(query_text: str, relevant_ids: List[str], user_context) -> Dict[str, dict]:
    from backend.retrieval.models import RetrievalQuery
    from backend.retrieval.vector_search import vector_retriever
    from backend.retrieval.keyword_search import keyword_retriever
    from backend.retrieval.hybrid_search import hybrid_retriever
    from backend.rag.query_rewrite import rewrite_query

    base = RetrievalQuery(query_text=query_text, user_context=user_context)
    rewritten, _ = rewrite_query(query_text, [])
    rewritten_query = RetrievalQuery(query_text=rewritten, user_context=user_context)

    async def timed(label, coro):
        started = time.perf_counter()
        chunks = await coro
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        ranked = [chunk.chunk_id for chunk in chunks]
        metrics = score_ranking(relevant_ids, ranked)
        metrics["latency_ms"] = latency_ms
        metrics["returned"] = len(ranked)
        return label, metrics

    results = {}
    for label, coro in (
        ("dense_only", vector_retriever.retrieve(base)),
        ("bm25_only", keyword_retriever.retrieve(base)),
        ("hybrid_rrf", hybrid_retriever.retrieve(base)),
        ("hybrid_rrf_query_rewrite", hybrid_retriever.retrieve(rewritten_query)),
    ):
        name, metrics = await timed(label, coro)
        results[name] = metrics
    return results
