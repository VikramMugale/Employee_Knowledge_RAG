"""
Ingestion domain models, document lifecycle states, and chunk metadata schemas.
"""

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentState(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class ChunkMetadata(BaseModel):
    document_id: str
    document_title: str
    document_version: str
    section_title: Optional[str] = None
    subsection_title: Optional[str] = None
    paragraph_index: int = 0
    content_hash: str
    access_level: str = "PUBLIC_INTERNAL"
    department: Optional[str] = None
    allowed_roles: List[str] = Field(default_factory=list)
    embedding_model: str = "text-embedding-004"
    embedding_version: str = "v1"
    embedding_dimension: int = 768
    index_version: str = "v1"
    lifecycle_state: str = "ACTIVE"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    id: str
    title: str
    file_path: str
    file_type: str
    content_hash: str
    version: str = "2026.1"
    lifecycle_state: DocumentState = DocumentState.PENDING
    access_level: str = "PUBLIC_INTERNAL"
    department: Optional[str] = None
    owner: str = "Human Resources"
    effective_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None
