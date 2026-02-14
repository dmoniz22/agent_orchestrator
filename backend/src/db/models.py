"""SQLAlchemy ORM models for database persistence."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TaskStatus(str, PyEnum):
    """Task execution status."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_INPUT = "waiting_input"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, PyEnum):
    """Message role in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ActionType(str, PyEnum):
    """Type of step action."""
    AGENT_CALL = "agent_call"
    TOOL_CALL = "tool_call"
    FINAL_RESPONSE = "final_response"


class Session(Base):
    """User session model."""
    
    __tablename__ = "sessions"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict
    )
    
    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class Conversation(Base):
    """Conversation model for tracking multi-turn interactions."""
    
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    original_query: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    current_objective: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_conversations_session", "session_id"),
    )


class Message(Base):
    """Individual message in a conversation."""
    
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        # pgvector vector type - will be created by migration
        # Using ARRAY as placeholder, actual type is vector(1536)
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
    )


class AgentRun(Base):
    """Record of an agent invocation."""
    
    __tablename__ = "agent_runs"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    input: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    output: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="running"  # running, completed, failed
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="agent_runs")
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        "ToolCall",
        back_populates="agent_run",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_agent_runs_conversation", "conversation_id"),
    )


class ToolCall(Base):
    """Record of a tool invocation."""
    
    __tablename__ = "tool_calls"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    agent_run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False
    )
    tool_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )
    success: Mapped[bool | None] = mapped_column(
        nullable=True
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # Relationships
    agent_run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tool_calls")
    
    # Indexes
    __table_args__ = (
        Index("idx_tool_calls_agent_run", "agent_run_id"),
    )


class MemoryEmbedding(Base):
    """Long-term memory embeddings for semantic search."""
    
    __tablename__ = "memory_embeddings"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True
    )
    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(
        # pgvector vector type - will be created by migration
        # Using ARRAY as placeholder, actual type is vector(1536)
        nullable=False
    )
    metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # Relationships
    session: Mapped["Session | None"] = relationship("Session")
    
    # Indexes
    __table_args__ = (
        Index("idx_memory_embeddings_session", "session_id"),
        # Note: pgvector index created via migration
        # CREATE INDEX idx_memory_embedding_vector ON memory_embeddings
        #     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    )