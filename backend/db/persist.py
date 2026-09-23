"""
Optional Neon/Postgres persistence for documents and chunks.
"""

from backend.config.logging import logger
from backend.config.settings import settings
from backend.ingestion.models import Document, Chunk


async def persist_document(document: Document, chunks: list[Chunk]) -> None:
    if not settings.uses_postgres():
        return
    from backend.db.session import AsyncSessionLocal
    from backend.db.models.entities import DocumentEntity, ChunkEntity

    if AsyncSessionLocal is None:
        return
    try:
        async with AsyncSessionLocal() as session:
            existing = await session.get(DocumentEntity, document.id)
            if existing:
                existing.title = document.title
                existing.file_path = document.file_path
                existing.lifecycle_state = document.lifecycle_state.value
                existing.access_level = document.access_level
                existing.content_hash = document.content_hash
            else:
                session.add(
                    DocumentEntity(
                        id=document.id,
                        title=document.title,
                        file_path=document.file_path,
                        file_type=document.file_type,
                        content_hash=document.content_hash,
                        version=document.version,
                        lifecycle_state=document.lifecycle_state.value,
                        access_level=document.access_level,
                        department=document.department,
                        owner=document.owner,
                    )
                )
            for chunk in chunks:
                found = await session.get(ChunkEntity, chunk.id)
                payload = chunk.metadata.model_dump(mode="json")
                if found:
                    found.content = chunk.content
                    found.chunk_metadata = payload
                    found.chunk_index = chunk.chunk_index
                else:
                    session.add(
                        ChunkEntity(
                            id=chunk.id,
                            document_id=chunk.document_id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            chunk_metadata=payload,
                        )
                    )
            await session.commit()
    except Exception as exc:
        logger.error("[DB] Failed to persist document '%s': %s", document.title, exc)
