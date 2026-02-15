"""Short-term memory implementation (in-memory)."""

from collections import deque
from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from .base import BaseMemory, MemoryEntry

logger = get_logger(__name__)


class ShortTermMemory(BaseMemory):
    """Short-term memory for recent conversation context.
    
    Stores recent conversation turns in memory for quick access.
    Automatically evicts old entries when capacity is reached.
    """
    
    def __init__(self, max_entries: int = 50) -> None:
        """Initialize short-term memory.
        
        Args:
            max_entries: Maximum number of entries to store.
        """
        super().__init__("short_term")
        self.max_entries = max_entries
        self._memories: deque[MemoryEntry] = deque(maxlen=max_entries)
        
        logger.info(
            "ShortTermMemory initialized",
            max_entries=max_entries
        )
    
    async def store(
        self,
        content: str,
        session_id: UUID | None = None,
        importance: float = 1.0,
        metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        """Store a memory entry.
        
        Args:
            content: Memory content.
            session_id: Optional session identifier.
            importance: Importance score.
            metadata: Optional metadata.
            
        Returns:
            Stored memory entry.
        """
        entry = self._create_entry(
            content=content,
            session_id=session_id,
            memory_type="short_term",
            importance=importance,
            metadata=metadata
        )
        
        self._memories.append(entry)
        
        logger.debug(
            "Stored in short-term memory",
            memory_id=str(entry.memory_id),
            session_id=str(session_id) if session_id else None,
            current_size=len(self._memories)
        )
        
        return entry
    
    async def retrieve(
        self,
        query: str,
        session_id: UUID | None = None,
        limit: int = 5
    ) -> list[MemoryEntry]:
        """Retrieve relevant memories by simple keyword matching.
        
        Args:
            query: Search query.
            session_id: Optional session to filter by.
            limit: Maximum results.
            
        Returns:
            List of matching memory entries.
        """
        query_lower = query.lower()
        results = []
        
        # Search from most recent to oldest
        for entry in reversed(self._memories):
            # Filter by session if specified
            if session_id and entry.session_id != session_id:
                continue
            
            # Simple keyword matching
            if query_lower in entry.content.lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        
        logger.debug(
            "Retrieved from short-term memory",
            query=query[:50],
            results_found=len(results)
        )
        
        return results
    
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
        results = []
        
        # Iterate from most recent
        for entry in reversed(self._memories):
            if session_id and entry.session_id != session_id:
                continue
            
            results.append(entry)
            if len(results) >= limit:
                break
        
        return results
    
    async def clear(self, session_id: UUID | None = None) -> int:
        """Clear memories.
        
        Args:
            session_id: Optional session to clear (clear all if None).
            
        Returns:
            Number of entries cleared.
        """
        if session_id is None:
            count = len(self._memories)
            self._memories.clear()
            logger.info("Cleared all short-term memories", count=count)
            return count
        
        # Clear only entries for specific session
        original_count = len(self._memories)
        self._memories = deque(
            [m for m in self._memories if m.session_id != session_id],
            maxlen=self.max_entries
        )
        cleared_count = original_count - len(self._memories)
        
        logger.info(
            "Cleared session short-term memories",
            session_id=str(session_id),
            count=cleared_count
        )
        
        return cleared_count
    
    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics.
        
        Returns:
            Memory statistics.
        """
        return {
            "total_entries": len(self._memories),
            "max_entries": self.max_entries,
            "memory_type": self.memory_type
        }
