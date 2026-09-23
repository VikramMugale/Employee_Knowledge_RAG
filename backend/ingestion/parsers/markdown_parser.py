"""
Markdown and text structure-aware document parser with token-budget chunking.
"""

import os
import re
import uuid
import hashlib
from typing import List, Optional
from backend.ingestion.parsers.base import DocumentParser
from backend.ingestion.models import Chunk, ChunkMetadata
from backend.ingestion.chunking import window_section
from backend.config.settings import settings


class MarkdownParser(DocumentParser):
    def compute_sha256(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

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
            raise FileNotFoundError(f"Policy file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as handle:
            full_content = handle.read()
        content_hash = self.compute_sha256(full_content)
        doc_basename = document_title or os.path.basename(file_path).replace(".md", "").replace("_", " ").title()
        max_tokens = getattr(settings, "chunk_max_tokens", 550)
        overlap_tokens = getattr(settings, "chunk_overlap_tokens", 80)
        sections = re.split(r"\n(?=#{1,3}\s)", full_content)
        chunks: List[Chunk] = []
        section_title = None
        chunk_idx = 0
        for sec in sections:
            sec_text = sec.strip()
            if not sec_text:
                continue
            lines = sec_text.splitlines()
            if lines[0].startswith("#"):
                section_title = lines[0].lstrip("#").strip()
                body = "\n".join(lines[1:]).strip() or sec_text
            else:
                body = sec_text
            for title, piece in window_section(section_title or "General", body, max_tokens, overlap_tokens):
                metadata = ChunkMetadata(
                    document_id=document_id,
                    document_title=doc_basename,
                    document_version=document_version,
                    section_title=title,
                    paragraph_index=chunk_idx,
                    content_hash=content_hash,
                    access_level=access_level,
                    lifecycle_state=lifecycle_state,
                )
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        chunk_index=chunk_idx,
                        content=piece,
                        metadata=metadata,
                    )
                )
                chunk_idx += 1
        return chunks
