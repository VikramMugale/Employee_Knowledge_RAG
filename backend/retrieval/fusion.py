"""
Reciprocal Rank Fusion (RRF) algorithm for aggregating vector and keyword search candidates.
"""

from typing import List, Dict
from backend.retrieval.models import CandidateChunk
from backend.config.settings import settings


class ReciprocalRankFusion:
    """Combines vector dense search and BM25 sparse search candidate lists using RRF score ranking."""

    def fuse(
        self,
        dense_candidates: List[CandidateChunk],
        sparse_candidates: List[CandidateChunk],
        k: int = 60,
        fusion_top_k: int = 30
    ) -> List[CandidateChunk]:
        """
        RRF Score Formula: sum(1.0 / (k + rank)) across all retrievers.
        """
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, CandidateChunk] = {}

        # 1. Process dense vector ranks
        for rank, candidate in enumerate(dense_candidates):
            cid = candidate.chunk_id
            chunk_map[cid] = candidate
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        # 2. Process sparse BM25 ranks
        for rank, candidate in enumerate(sparse_candidates):
            cid = candidate.chunk_id
            if cid not in chunk_map:
                chunk_map[cid] = candidate
            else:
                # Merge sparse score into candidate model
                chunk_map[cid].bm25_score = candidate.bm25_score
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        # 3. Assign fusion score and sort
        fused_list: List[CandidateChunk] = []
        for cid, rrf_score in scores.items():
            candidate = chunk_map[cid]
            candidate.fusion_score = round(rrf_score, 6)
            fused_list.append(candidate)

        fused_list.sort(key=lambda c: c.fusion_score or 0.0, reverse=True)
        return fused_list[:fusion_top_k]


rrf_fusion = ReciprocalRankFusion()
