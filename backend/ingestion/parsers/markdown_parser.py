"""
Markdown and text structure-aware document parser.
"""

import os
import re
import uuid
import hashlib
from typing import List, Optional
from backend.ingestion.parsers.base import DocumentParser
from backend.ingestion.models import Chunk, ChunkMetadata


class MarkdownParser(DocumentParser):
    """Structure-aware parser for Markdown policy documents."""

    def compute_sha256(self, content: str) -> str:
        """Compute SHA-256 hash of document string content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def parse(
        self,
        file_path: str,
        document_id: str,
        access_level: str = "PUBLIC_INTERNAL",
        document_title: Optional[str] = None,
        document_version: str = "2026.1",
    ) -> List[Chunk]:
        """Parse markdown file into structured section chunks."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Policy file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as handle:
            full_content = handle.read()

        content_hash = self.compute_sha256(full_content)
        doc_basename = document_title or os.path.basename(file_path).replace(".md", "").replace("_", " ").title()

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

            metadata = ChunkMetadata(
                document_id=document_id,
                document_title=doc_basename,
                document_version=document_version,
                section_title=section_title,
                paragraph_index=chunk_idx,
                content_hash=content_hash,
                access_level=access_level,
            )

            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=chunk_idx,
                    content=sec_text,
                    metadata=metadata,
                )
            )
            chunk_idx += 1

        return chunks
