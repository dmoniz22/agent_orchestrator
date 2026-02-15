"""Long-term memory implementation using pgvector."""

from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from src.memory.base import BaseMemory, MemoryEntry

logger = get_logger(__name__)


class LongTermMemory(BaseMemory):
    """Long-term memory with vector embeddings.
    
    Stores memories with embeddings for semantic similarity search.
    Uses pgvector extension for vector operations.
    """
    
    def __init__(
        self,
        embedding_provider=None,
        similarity_threshold: float = 0.7
    ) -> None:
        """Initialize long-term memory.
        
        Args:
            embedding_provider: Provider for generating embeddings.
            similarity_threshold: Minimum similarity score (0.0 to 1.0).
        """
        super().__init__("long_term")
        self.embedding_provider = embedding_provider
        self.similarity_threshold = similarity_threshold
        self._memories: list[MemoryEntry] = []  # In-memory for now
        
        logger.info(
            "LongTermMemory initialized",
            similarity_threshold=similarity_threshold
        )
    
    async def store(
        self,
        content: str,
        session_id: UUID | None = None,
        importance: float = 1.0,
        metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        """Store a memory with embedding.
        
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
            memory_type="long_term",
            importance=importance,
            metadata=metadata
        )
        
        # Generate embedding if provider available
        if self.embedding_provider:
            try:
                entry.embedding = await self.embedding_provider.embed(content)
                logger.debug(
                    "Generated embedding for memory",
                    memory_id=str(entry.memory_id),
                    embedding_dim=len(entry.embedding) if entry.embedding else 0
                )
            except Exception as e:
                logger.warning(
                    "Failed to generate embedding",
                    memory_id=str(entry.memory_id),
                    error=str(e)
                )
        
        self._memories.append(entry)
        
        logger.info(
            "Stored in long-term memory",
            memory_id=str(entry.memory_id),
            session_id=str(session_id) if session_id else None,
            has_embedding=entry.embedding is not None
        )
        
        return entry
    
    async def retrieve(
        self,
        query: str,
        session_id: UUID | None = None,
        limit: int = 5
    ) -> list[MemoryEntry]:
        """Retrieve memories by semantic similarity.
        
        Args:
            query: Search query.
            session_id: Optional session to filter by.
            limit: Maximum results.
            
        Returns:
            List of relevant memory entries sorted by similarity.
        """
        if not self.embedding_provider:
            # Fall back to keyword search
            return await self._keyword_search(query, session_id, limit)
        
        try:
            # Generate query embedding
            query_embedding = await self.embedding_provider.embed(query)
            
            # Calculate similarities
            scored_memories = []
            for entry in self._memories:
                # Filter by session if specified
                if session_id and entry.session_id != session_id:
                    continue
                
                if entry.embedding:
                    similarity = self._cosine_similarity(
                        query_embedding,
                        entry.embedding
                    )
                    if similarity >= self.similarity_threshold:
                        scored_memories.append((entry, similarity))
            
            # Sort by similarity and return top results
            scored_memories.sort(key=lambda x: x[1], reverse=True)
            results = [entry for entry, _ in scored_memories[:limit]]
            
            logger.debug(
                "Retrieved from long-term memory (semantic)",
                query=query[:50],
                results_found=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Semantic search failed, falling back to keyword",
                error=str(e)
            )
            return await self._keyword_search(query, session_id, limit)
    
    async def _keyword_search(
        self,
        query: str,
        session_id: UUID | None,
        limit: int
    ) -> list[MemoryEntry]:
        """Fallback keyword search.
        
        Args:
            query: Search query.
            session_id: Session filter.
            limit: Maximum results.
            
        Returns:
            Matching entries.
        """
        query_lower = query.lower()
        results = []
        
        for entry in self._memories:
            if session_id and entry.session_id != session_id:
                continue
            
            if query_lower in entry.content.lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        
        logger.debug(
            "Retrieved from long-term memory (keyword)",
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
        
        # Iterate from most recent (end of list)
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
            logger.info("Cleared all long-term memories", count=count)
            return count
        
        # Clear only entries for specific session
        original_count = len(self._memories)
        self._memories = [
            m for m in self._memories if m.session_id != session_id
        ]
        cleared_count = original_count - len(self._memories)
        
        logger.info(
            "Cleared session long-term memories",
            session_id=str(session_id),
            count=cleared_count
        )
        
        return cleared_count
    
    def _cosine_similarity(
        self,
        vec1: list[float],
        vec2: list[float]
    ) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector.
            vec2: Second vector.
            
        Returns:
            Cosine similarity score (0.0 to 1.0).
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics.
        
        Returns:
            Memory statistics.
        """
        embedded_count = sum(1 for m in self._memories if m.embedding is not None)
        
        return {
            "total_entries": len(self._memories),
            "embedded_entries": embedded_count,
            "similarity_threshold": self.similarity_threshold,
            "memory_type": self.memory_type
        }
