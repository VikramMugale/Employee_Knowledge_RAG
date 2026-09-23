"""PDF parser using pypdf, then the same token-budget chunker as Markdown."""
import os
import uuid
import hashlib
from typing import List, Optional
from backend.ingestion.models import Chunk, ChunkMetadata
from backend.ingestion.chunking import window_section
from backend.config.settings import settings


class PdfParser:
    def compute_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def parse(
        self,
        file_path: str,
        document_id: str,
        access_level: str = "PUBLIC_INTERNAL",
        document_title: Optional[str] = None,
        document_version: str = "2026.1",
        lifecycle_state: str = "ACTIVE",
    ) -> List[Chunk]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)
        from pypdf import PdfReader
        with open(file_path, "rb") as handle:
            raw = handle.read()
        content_hash = self.compute_sha256(raw)
        reader = PdfReader(file_path)
        pages = []
        for index, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append((f"Page {index + 1}", text))
        if not pages:
            raise ValueError("No extractable text in PDF")
        doc_title = document_title or os.path.basename(file_path).rsplit(".", 1)[0].replace("_", " ").title()
        max_tokens = getattr(settings, "chunk_max_tokens", 550)
        overlap = getattr(settings, "chunk_overlap_tokens", 80)
        chunks: List[Chunk] = []
        chunk_idx = 0
        for section_title, body in pages:
            for title, piece in window_section(section_title, body, max_tokens, overlap):
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        chunk_index=chunk_idx,
                        content=piece,
                        metadata=ChunkMetadata(
                            document_id=document_id,
                            document_title=doc_title,
                            document_version=document_version,
                            section_title=title,
                            paragraph_index=chunk_idx,
                            content_hash=content_hash,
                            access_level=access_level,
                            lifecycle_state=lifecycle_state,
                        ),
                    )
                )
                chunk_idx += 1
        return chunks
