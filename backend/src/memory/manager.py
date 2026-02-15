"""Memory manager for coordinating short-term and long-term memory."""

from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from .base import BaseMemory, MemoryEntry
from .short_term import ShortTermMemory
from .long_term import LongTermMemory

logger = get_logger(__name__)


class MemoryManager:
    """Coordinates short-term and long-term memory systems.
    
    Provides unified interface for:
    - Storing conversation history (short-term)
    - Storing important facts/preferences (long-term)
    - Retrieving relevant context from both
    """
    
    def __init__(
        self,
        short_term: ShortTermMemory | None = None,
        long_term: LongTermMemory | None = None,
        auto_save_to_long_term: bool = False,
        importance_threshold: float = 0.7
    ) -> None:
        """Initialize memory manager.
        
        Args:
            short_term: Short-term memory instance.
            long_term: Long-term memory instance.
            auto_save_to_long_term: Auto-save high-importance memories.
            importance_threshold: Threshold for auto-saving.
        """
        self.short_term = short_term or ShortTermMemory()
        self.long_term = long_term or LongTermMemory()
        self.auto_save_to_long_term = auto_save_to_long_term
        self.importance_threshold = importance_threshold
        
        logger.info(
            "MemoryManager initialized",
            auto_save=auto_save_to_long_term,
            threshold=importance_threshold
        )
    
    async def store(
        self,
        content: str,
        session_id: UUID | None = None,
        importance: float = 0.5,
        memory_type: str = "generic",
        metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        """Store a memory in appropriate system.
        
        Args:
            content: Memory content.
            session_id: Optional session identifier.
            importance: Importance score (0.0 to 1.0).
            memory_type: Type of memory.
            metadata: Optional metadata.
            
        Returns:
            Stored memory entry.
        """
        # Always store in short-term for recent context
        entry = await self.short_term.store(
            content=content,
            session_id=session_id,
            importance=importance,
            metadata={**metadata, "memory_type": memory_type} if metadata else {"memory_type": memory_type}
        )
        
        # Store in long-term if high importance or auto-save enabled
        if importance >= self.importance_threshold or self.auto_save_to_long_term:
            await self.long_term.store(
                content=content,
                session_id=session_id,
                importance=importance,
                metadata={**metadata, "memory_type": memory_type} if metadata else {"memory_type": memory_type}
            )
        
        return entry
    
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
        return await self.short_term.store_conversation_turn(
            role=role,
            content=content,
            session_id=session_id,
            metadata=metadata
        )
    
    async def retrieve_context(
        self,
        query: str,
        session_id: UUID | None = None,
        short_term_limit: int = 10,
        long_term_limit: int = 5
    ) -> dict[str, list[MemoryEntry]]:
        """Retrieve context from both memory systems.
        
        Args:
            query: Search query.
            session_id: Optional session to filter by.
            short_term_limit: Max short-term results.
            long_term_limit: Max long-term results.
            
        Returns:
            Dictionary with 'short_term' and 'long_term' entries.
        """
        # Retrieve from both systems concurrently
        import asyncio
        
        short_term_task = self.short_term.retrieve(
            query=query,
            session_id=session_id,
            limit=short_term_limit
        )
        
        long_term_task = self.long_term.retrieve(
            query=query,
            session_id=session_id,
            limit=long_term_limit
        )
        
        short_term_results, long_term_results = await asyncio.gather(
            short_term_task,
            long_term_task
        )
        
        logger.debug(
            "Retrieved context",
            query=query[:50],
            short_term_count=len(short_term_results),
            long_term_count=len(long_term_results)
        )
        
        return {
            "short_term": short_term_results,
            "long_term": long_term_results
        }
    
    async def get_conversation_history(
        self,
        session_id: UUID,
        limit: int = 20
    ) -> list[MemoryEntry]:
        """Get conversation history for a session.
        
        Args:
            session_id: Session identifier.
            limit: Maximum number of turns.
            
        Returns:
            List of conversation entries.
        """
        # Get recent entries from short-term memory
        all_recent = await self.short_term.get_recent(
            session_id=session_id,
            limit=limit * 2  # Get extra in case there are non-conversation entries
        )
        
        # Filter for conversation entries
        conversation = [
            entry for entry in all_recent
            if entry.metadata.get("role") in ["user", "assistant", "system"]
        ]
        
        return conversation[:limit]
    
    async def clear_session(self, session_id: UUID) -> dict[str, int]:
        """Clear all memories for a session.
        
        Args:
            session_id: Session to clear.
            
        Returns:
            Counts of cleared entries per system.
        """
        import asyncio
        
        short_term_count = await self.short_term.clear(session_id)
        long_term_count = await self.long_term.clear(session_id)
        
        logger.info(
            "Cleared session memories",
            session_id=str(session_id),
            short_term=short_term_count,
            long_term=long_term_count
        )
        
        return {
            "short_term": short_term_count,
            "long_term": long_term_count
        }
    
    async def consolidate_to_long_term(
        self,
        session_id: UUID,
        importance_threshold: float | None = None
    ) -> int:
        """Consolidate important short-term memories to long-term.
        
        Args:
            session_id: Session to consolidate.
            importance_threshold: Minimum importance to consolidate.
            
        Returns:
            Number of memories consolidated.
        """
        threshold = importance_threshold or self.importance_threshold
        
        # Get all short-term memories for session
        short_term_memories = await self.short_term.get_recent(
            session_id=session_id,
            limit=1000  # Get all
        )
        
        consolidated = 0
        for entry in short_term_memories:
            if entry.importance >= threshold:
                await self.long_term.store(
                    content=entry.content,
                    session_id=entry.session_id,
                    importance=entry.importance,
                    metadata=entry.metadata
                )
                consolidated += 1
        
        logger.info(
            "Consolidated memories to long-term",
            session_id=str(session_id),
            consolidated=consolidated
        )
        
        return consolidated
    
    def get_stats(self) -> dict[str, Any]:
        """Get memory system statistics.
        
        Returns:
            Combined statistics.
        """
        return {
            "short_term": self.short_term.get_stats(),
            "long_term": self.long_term.get_stats(),
            "auto_save_to_long_term": self.auto_save_to_long_term,
            "importance_threshold": self.importance_threshold
        }
