"""Document ingestion engine with SHA-256 idempotency and lifecycle state management."""

import os
from typing import List, Dict, Optional
from backend.ingestion.models import Document, Chunk, DocumentState
from backend.ingestion.parsers.markdown_parser import MarkdownParser
from backend.ingestion.parsers.pdf_parser import PdfParser
from backend.ingestion.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from backend.retrieval.vector_search import vector_retriever
from backend.retrieval.keyword_search import keyword_retriever
from backend.config.logging import logger
from backend.guardrails.pii import pii_guardrail


class IngestionPipeline:
    def __init__(self):
        self.markdown_parser = MarkdownParser()
        self.pdf_parser = PdfParser()
        self.embedding_provider = GeminiEmbeddingProvider()
        self.processed_hashes: Dict[str, str] = {}
        self.documents_registry: Dict[str, Document] = {}
        self.chunks_registry: Dict[str, List[Chunk]] = {}

    def compute_file_hash(self, file_path: str) -> str:
        import hashlib
        hasher = hashlib.sha256()
        with open(file_path, "rb") as handle:
            while chunk := handle.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def ingest_file(self, file_path: str, access_level: str = "PUBLIC_INTERNAL") -> Optional[Document]:
        if not os.path.exists(file_path):
            logger.error(f"Ingestion failed: File does not exist at {file_path}")
            return None
        content_hash = self.compute_file_hash(file_path)
        if content_hash in self.processed_hashes:
            existing_doc_id = self.processed_hashes[content_hash]
            existing = self.documents_registry.get(existing_doc_id)
            chunks = self.chunks_registry.get(existing_doc_id) or []
            if chunks:
                vector_retriever.index_chunks(chunks)
                keyword_retriever.index_chunks(chunks)
            return existing
        doc_title = os.path.basename(file_path).rsplit(".", 1)[0].replace("_", " ").title()
        doc_id = f"doc_{content_hash[:12]}"
        suffix = file_path.rsplit(".", 1)[-1].lower()
        doc = Document(
            id=doc_id,
            title=doc_title,
            file_path=file_path,
            file_type=suffix,
            content_hash=content_hash,
            lifecycle_state=DocumentState.PROCESSING,
            access_level=access_level,
        )
        try:
            parser = self.pdf_parser if suffix == "pdf" else self.markdown_parser
            chunks = await parser.parse(
                file_path,
                doc_id,
                access_level=access_level,
                document_title=doc_title,
                document_version=doc.version,
            )
            for chunk in chunks:
                pii_result = await pii_guardrail.validate(chunk.content)
                if pii_result.sanitized_content:
                    chunk.content = pii_result.sanitized_content
            embeddings = await self.embedding_provider.embed_texts([chunk.content for chunk in chunks])
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
                chunk.metadata.embedding_model = "text-embedding-004"
                chunk.metadata.embedding_dimension = len(embedding)
            vector_retriever.index_chunks(chunks)
            keyword_retriever.index_chunks(chunks)
            doc.lifecycle_state = DocumentState.ACTIVE
            self.processed_hashes[content_hash] = doc_id
            self.documents_registry[doc_id] = doc
            self.chunks_registry[doc_id] = chunks
            from backend.db.persist import persist_document
            await persist_document(doc, chunks)
            logger.info(
                f"[INGESTION SUCCESS] Ingested '{doc.title}' ({len(chunks)} chunks, state={doc.lifecycle_state.value})"
            )
            return doc
        except Exception as exc:
            doc.lifecycle_state = DocumentState.FAILED
            logger.error(f"[INGESTION ERROR] Failed to ingest {file_path}: {str(exc)}")
            raise

    async def ingest_directory(self, seed_dir: str, access_level: str = "PUBLIC_INTERNAL") -> List[Document]:
        if not os.path.exists(seed_dir):
            return []
        ingested: List[Document] = []
        for fname in sorted(os.listdir(seed_dir)):
            if not fname.lower().endswith((".md", ".pdf", ".txt", ".markdown")):
                continue
            document = await self.ingest_file(os.path.join(seed_dir, fname), access_level=access_level)
            if document:
                ingested.append(document)
        return ingested


ingestion_pipeline = IngestionPipeline()
