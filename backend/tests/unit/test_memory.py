"""Tests for memory system."""

import pytest
from uuid import uuid4

from src.memory.base import MemoryEntry
from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory
from src.memory.manager import MemoryManager


class TestMemoryEntry:
    """Test cases for MemoryEntry."""
    
    def test_memory_entry_creation(self):
        """Test creating a memory entry."""
        entry = MemoryEntry(
            content="Test content",
            memory_type="conversation"
        )
        
        assert entry.content == "Test content"
        assert entry.memory_type == "conversation"
        assert entry.importance == 1.0
        assert entry.memory_id is not None
    
    def test_memory_entry_to_dict(self):
        """Test converting entry to dictionary."""
        entry = MemoryEntry(
            content="Test content",
            memory_type="fact",
            importance=0.8
        )
        
        data = entry.to_dict()
        
        assert data["content"] == "Test content"
        assert data["memory_type"] == "fact"
        assert data["importance"] == 0.8
        assert "memory_id" in data


class TestShortTermMemory:
    """Test cases for ShortTermMemory."""
    
    @pytest.fixture
    def memory(self):
        """Create fresh short-term memory."""
        return ShortTermMemory(max_entries=10)
    
    @pytest.mark.asyncio
    async def test_store_memory(self, memory):
        """Test storing a memory."""
        entry = await memory.store(
            content="Test memory",
            importance=0.9
        )
        
        assert entry.content == "Test memory"
        assert entry.importance == 0.9
        assert len(memory._memories) == 1
    
    @pytest.mark.asyncio
    async def test_retrieve_by_keyword(self, memory):
        """Test retrieving memories by keyword."""
        await memory.store("Python is great")
        await memory.store("JavaScript is nice")
        await memory.store("Python is powerful")
        
        results = await memory.retrieve("Python")
        
        assert len(results) == 2
        assert all("Python" in r.content for r in results)
    
    @pytest.mark.asyncio
    async def test_retrieve_by_session(self, memory):
        """Test retrieving memories filtered by session."""
        session1 = uuid4()
        session2 = uuid4()
        
        await memory.store("Session 1 content", session_id=session1)
        await memory.store("Session 2 content", session_id=session2)
        
        results = await memory.retrieve("content", session_id=session1)
        
        assert len(results) == 1
        assert results[0].content == "Session 1 content"
    
    @pytest.mark.asyncio
    async def test_get_recent(self, memory):
        """Test getting recent memories."""
        await memory.store("First")
        await memory.store("Second")
        await memory.store("Third")
        
        results = await memory.get_recent(limit=2)
        
        assert len(results) == 2
        assert results[0].content == "Third"
        assert results[1].content == "Second"
    
    @pytest.mark.asyncio
    async def test_clear_all(self, memory):
        """Test clearing all memories."""
        await memory.store("Content 1")
        await memory.store("Content 2")
        
        count = await memory.clear()
        
        assert count == 2
        assert len(memory._memories) == 0
    
    @pytest.mark.asyncio
    async def test_clear_session(self, memory):
        """Test clearing memories for specific session."""
        session = uuid4()
        
        await memory.store("Session content", session_id=session)
        await memory.store("Other content")
        
        count = await memory.clear(session_id=session)
        
        assert count == 1
        assert len(memory._memories) == 1
    
    @pytest.mark.asyncio
    async def test_max_entries(self):
        """Test memory eviction at max capacity."""
        memory = ShortTermMemory(max_entries=3)
        
        await memory.store("First")
        await memory.store("Second")
        await memory.store("Third")
        await memory.store("Fourth")  # Should evict "First"
        
        assert len(memory._memories) == 3
        contents = [m.content for m in memory._memories]
        assert "First" not in contents
        assert "Fourth" in contents


class TestLongTermMemory:
    """Test cases for LongTermMemory."""
    
    @pytest.fixture
    def memory(self):
        """Create fresh long-term memory."""
        return LongTermMemory(similarity_threshold=0.5)
    
    @pytest.mark.asyncio
    async def test_store_memory(self, memory):
        """Test storing a memory."""
        entry = await memory.store(
            content="Test long-term memory",
            importance=0.9
        )
        
        assert entry.content == "Test long-term memory"
        assert len(memory._memories) == 1
    
    @pytest.mark.asyncio
    async def test_keyword_search_fallback(self, memory):
        """Test keyword search when no embeddings."""
        await memory.store("Python programming")
        await memory.store("JavaScript coding")
        
        results = await memory.retrieve("Python")
        
        assert len(results) == 1
        assert "Python" in results[0].content
    
    @pytest.mark.asyncio
    async def test_clear_session(self, memory):
        """Test clearing session memories."""
        session = uuid4()
        
        await memory.store("Session", session_id=session)
        await memory.store("General")
        
        count = await memory.clear(session_id=session)
        
        assert count == 1
        assert len(memory._memories) == 1
    
    def test_cosine_similarity(self, memory):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]
        
        # Same vectors = 1.0
        assert memory._cosine_similarity(vec1, vec2) == 1.0
        
        # Orthogonal vectors = 0.0
        assert memory._cosine_similarity(vec1, vec3) == 0.0


class TestMemoryManager:
    """Test cases for MemoryManager."""
    
    @pytest.fixture
    def manager(self):
        """Create fresh memory manager."""
        return MemoryManager(
            auto_save_to_long_term=False,
            importance_threshold=0.7
        )
    
    @pytest.mark.asyncio
    async def test_store_routing(self, manager):
        """Test that stores go to short-term."""
        entry = await manager.store(
            content="Test content",
            importance=0.5
        )
        
        # Should be in short-term
        assert len(manager.short_term._memories) == 1
        # Should NOT be in long-term (importance < threshold)
        assert len(manager.long_term._memories) == 0
    
    @pytest.mark.asyncio
    async def test_high_importance_to_long_term(self, manager):
        """Test high importance memories go to long-term."""
        entry = await manager.store(
            content="Important fact",
            importance=0.8
        )
        
        # Should be in both
        assert len(manager.short_term._memories) == 1
        assert len(manager.long_term._memories) == 1
    
    @pytest.mark.asyncio
    async def test_store_conversation_turn(self, manager):
        """Test storing conversation turns."""
        session = uuid4()
        
        entry = await manager.store_conversation_turn(
            role="user",
            content="Hello",
            session_id=session
        )
        
        assert entry.metadata["role"] == "user"
        assert entry.content == "Hello"
        assert entry.session_id == session
    
    @pytest.mark.asyncio
    async def test_retrieve_context(self, manager):
        """Test retrieving context from both systems."""
        await manager.store("Python info", importance=0.8)  # Goes to both
        await manager.store("Other info", importance=0.3)   # Short-term only
        
        context = await manager.retrieve_context("Python")
        
        assert "short_term" in context
        assert "long_term" in context
        # Should find in both
        assert len(context["long_term"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, manager):
        """Test getting conversation history."""
        session = uuid4()
        
        await manager.store_conversation_turn("user", "Hello", session)
        await manager.store_conversation_turn("assistant", "Hi!", session)
        await manager.store("Not conversation", session_id=session)
        
        history = await manager.get_conversation_history(session)
        
        assert len(history) == 2
        # Most recent first
        assert history[0].metadata["role"] == "assistant"
        assert history[1].metadata["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_clear_session(self, manager):
        """Test clearing session from both systems."""
        session = uuid4()
        
        await manager.store("Content", session_id=session, importance=0.8)
        
        counts = await manager.clear_session(session)
        
        assert counts["short_term"] == 1
        assert counts["long_term"] == 1
        assert len(manager.short_term._memories) == 0
        assert len(manager.long_term._memories) == 0
    
    @pytest.mark.asyncio
    async def test_consolidate_to_long_term(self, manager):
        """Test consolidating important memories."""
        session = uuid4()
        
        await manager.short_term.store("Important", session_id=session, importance=0.8)
        await manager.short_term.store("Not important", session_id=session, importance=0.3)
        
        count = await manager.consolidate_to_long_term(session)
        
        assert count == 1
        assert len(manager.long_term._memories) == 1
    
    def test_get_stats(self, manager):
        """Test getting memory statistics."""
        stats = manager.get_stats()
        
        assert "short_term" in stats
        assert "long_term" in stats
        assert "auto_save_to_long_term" in stats
        assert "importance_threshold" in stats