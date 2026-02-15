"""Base memory interface for all memory types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """Single memory entry."""
    
    content: str
    memory_id: UUID = field(default_factory=uuid4)
    session_id: UUID | None = None
    memory_type: str = "generic"  # "conversation", "fact", "preference", etc.
    importance: float = 1.0  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory_id": str(self.memory_id),
            "session_id": str(self.session_id) if self.session_id else None,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "has_embedding": self.embedding is not None
        }


class BaseMemory(ABC):
    """Abstract base class for memory systems.
    
    Provides common interface for:
    - Storing memories
    - Retrieving memories
    - Searching by similarity (for vector stores)
    """
    
    def __init__(self, memory_type: str) -> None:
        """Initialize memory system.
        
        Args:
            memory_type: Type identifier for this memory.
        """
        self.memory_type = memory_type
        logger.info("Memory system initialized", memory_type=memory_type)
    
    @abstractmethod
    async def store(
        self,
        content: str,
        session_id: UUID | None = None,
        importance: float = 1.0,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> MemoryEntry:
        """Store a memory.
        
        Args:
            content: Memory content.
            session_id: Optional session identifier.
            importance: Importance score (0.0 to 1.0).
            metadata: Optional metadata.
            **kwargs: Additional implementation-specific parameters.
            
        Returns:
            Stored memory entry.
        """
        pass
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        session_id: UUID | None = None,
        limit: int = 5
    ) -> list[MemoryEntry]:
        """Retrieve relevant memories.
        
        Args:
            query: Search query.
            session_id: Optional session to filter by.
            limit: Maximum results.
            
        Returns:
            List of relevant memory entries.
        """
        pass
    
    @abstractmethod
    async def get_recent(
        self,
        session_id: UUID | None = None,
        limit: int = 10
    ) -> list[MemoryEntry]:
        """Get recent memories.
        
        Args:
            session_id: Optional session to filter by.
            limit: Maximum results.
            
        Returns:
            List of recent memory entries.
        """
        pass
    
    @abstractmethod
    async def clear(self, session_id: UUID | None = None) -> int:
        """Clear memories.
        
        Args:
            session_id: Optional session to clear (clear all if None).
            
        Returns:
            Number of entries cleared.
        """
        pass
    
    async def store_conversation_turn(
        self,
        role: str,
        content: str,
        session_id: UUID,
        metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        """Store a conversation turn.
        
        Args:
            role: Speaker role ("user", "assistant", "system").
            content: Message content.
            session_id: Session identifier.
            metadata: Optional metadata.
            
        Returns:
            Stored memory entry.
        """
        meta = metadata or {}
        meta["role"] = role
        meta["memory_type"] = "conversation"
        
        return await self.store(
            content=content,
            session_id=session_id,
            importance=0.8 if role == "user" else 0.6,
            metadata=meta
        )
    
    def _create_entry(
        self,
        content: str,
        session_id: UUID | None,
        memory_type: str,
        importance: float,
        metadata: dict[str, Any] | None
    ) -> MemoryEntry:
        """Create a memory entry.
        
        Args:
            content: Memory content.
            session_id: Session ID.
            memory_type: Type of memory.
            importance: Importance score.
            metadata: Optional metadata.
            
        Returns:
            Memory entry.
        """
        return MemoryEntry(
            content=content,
            session_id=session_id,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )
