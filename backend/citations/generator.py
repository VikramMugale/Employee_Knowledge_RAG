"""
Citation generator with lexical claim-to-chunk alignment.
"""

import re
from typing import List
from backend.citations.base import CitationGenerator
from backend.rag.models import CitationItem
from backend.retrieval.models import CandidateChunk


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "is", "are",
    "with", "by", "at", "from", "that", "this", "it", "be", "as", "you", "your",
}


def _tokens(text: str) -> set:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in _STOPWORDS and len(word) > 2}


def _claims(answer: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", answer.strip())
    return [part.strip() for part in parts if part.strip() and len(part.split()) >= 4]


class StandardCitationGenerator(CitationGenerator):
    async def generate_citations(self, answer: str, source_chunks: List[CandidateChunk]) -> List[CitationItem]:
        citations: List[CitationItem] = []
        seen = set()
        claims = _claims(answer) or ([answer] if answer.strip() else [])
        if not claims:
            for idx, chunk in enumerate(source_chunks[:5]):
                citations.append(self._item(idx, chunk, chunk.content))
            return citations
        for idx, claim in enumerate(claims):
            claim_tokens = _tokens(claim)
            best = None
            best_score = 0.0
            for chunk in source_chunks:
                chunk_tokens = _tokens(chunk.content)
                if not claim_tokens or not chunk_tokens:
                    continue
                overlap = len(claim_tokens & chunk_tokens) / max(1, len(claim_tokens))
                if overlap > best_score:
                    best_score = overlap
                    best = chunk
            if best is None or best_score < 0.18:
                continue
            key = f"{best.metadata.document_title}_{best.metadata.section_title}"
            if key in seen:
                continue
            seen.add(key)
            citations.append(self._item(idx, best, claim, confidence=round(best_score, 3)))
        return citations

    def _item(self, idx: int, chunk: CandidateChunk, snippet: str, confidence: float = 0.0) -> CitationItem:
        return CitationItem(
            id=f"cite_{idx + 1}",
            document_title=chunk.metadata.document_title,
            document_version=chunk.metadata.document_version,
            section_title=chunk.metadata.section_title or "General Policy",
            snippet=(snippet[:180] + "...") if len(snippet) > 180 else snippet,
        )


citation_generator = StandardCitationGenerator()
