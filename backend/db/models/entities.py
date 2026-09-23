"""
SQLAlchemy database entity models for users, documents, chunks, conversations, feedback, and LLMOps.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.session import Base
from backend.ingestion.models import DocumentState
from backend.auth.models import Role


class UserEntity(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=Role.EMPLOYEE.value, nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="General", nullable=False)
    location: Mapped[str] = mapped_column(String(100), default="Global", nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), default="full_time", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentEntity(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # SHA-256
    version: Mapped[str] = mapped_column(String(50), default="2026.1", nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(50), default=DocumentState.PENDING.value, nullable=False)
    access_level: Mapped[str] = mapped_column(String(50), default="PUBLIC_INTERNAL", nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    owner: Mapped[str] = mapped_column(String(100), default="Human Resources", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks: Mapped[list["ChunkEntity"]] = relationship("ChunkEntity", back_populates="document", cascade="all, delete-orphan")


class ChunkEntity(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    document: Mapped["DocumentEntity"] = relationship("DocumentEntity", back_populates="chunks")


class ConversationEntity(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New Conversation", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    messages: Mapped[list["MessageEntity"]] = relationship("MessageEntity", back_populates="conversation", cascade="all, delete-orphan")


class MessageEntity(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[dict] = mapped_column(JSON, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    conversation: Mapped["ConversationEntity"] = relationship("ConversationEntity", back_populates="messages")


class FeedbackEntity(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 (helpful) or -1 (not helpful)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
