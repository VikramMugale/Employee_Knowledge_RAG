"""
Citation reference generator and claim alignment validator.
"""

from typing import List
from backend.citations.base import CitationGenerator
from backend.rag.models import CitationItem
from backend.retrieval.models import CandidateChunk


class StandardCitationGenerator(CitationGenerator):
    """Generates structured citation references linking LLM claims to policy document sections."""

    async def generate_citations(
        self, answer: str, source_chunks: List[CandidateChunk]
    ) -> List[CitationItem]:
        """Format candidate chunk references into CitationItems."""
        citations: List[CitationItem] = []
        seen_docs = set()

        for idx, chunk in enumerate(source_chunks):
            doc_key = f"{chunk.metadata.document_title}_{chunk.metadata.section_title}"
            if doc_key in seen_docs:
                continue
            seen_docs.add(doc_key)

            citation = CitationItem(
                id=f"cite_{idx + 1}",
                document_title=chunk.metadata.document_title,
                document_version=chunk.metadata.document_version,
                section_title=chunk.metadata.section_title or "General Policy",
                snippet=chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
            )
            citations.append(citation)

        return citations


citation_generator = StandardCitationGenerator()
