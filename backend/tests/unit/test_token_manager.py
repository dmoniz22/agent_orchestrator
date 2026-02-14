"""Unit tests for the token manager."""

import pytest

from src.models.token_manager import (
    ContextWindowManager,
    TokenManager,
)


class TestTokenManager:
    """Test cases for TokenManager."""
    
    @pytest.fixture
    def token_manager(self):
        """Create token manager with default settings."""
        return TokenManager(chars_per_token=4)
    
    def test_estimate_tokens_simple(self, token_manager):
        """Test token estimation for simple text."""
        text = "Hello world"  # 11 characters
        tokens = token_manager.estimate_tokens(text)
        assert tokens == 2  # 11 // 4 = 2
    
    def test_estimate_tokens_empty(self, token_manager):
        """Test token estimation for empty string."""
        tokens = token_manager.estimate_tokens("")
        assert tokens == 0
    
    def test_estimate_tokens_long(self, token_manager):
        """Test token estimation for long text."""
        text = "a" * 1000  # 1000 characters
        tokens = token_manager.estimate_tokens(text)
        assert tokens == 250  # 1000 // 4
    
    def test_estimate_messages_tokens(self, token_manager):
        """Test token estimation for messages."""
        messages = [
            {"role": "system", "content": "You are helpful"},  # 15 chars = 3 tokens + 4 overhead
            {"role": "user", "content": "Hello"},  # 5 chars = 1 token + 4 overhead
        ]
        tokens = token_manager.estimate_messages_tokens(messages)
        # (15 // 4) + 4 + (5 // 4) + 4 = 3 + 4 + 1 + 4 = 12
        assert tokens == 12
    
    def test_truncate_messages_no_truncation_needed(self, token_manager):
        """Test truncation when no truncation is needed."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
        ]
        
        result = token_manager.truncate_messages(messages, max_tokens=100)
        
        # Should return all messages unchanged
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
    
    def test_truncate_messages_preserves_system(self, token_manager):
        """Test that system messages are preserved during truncation."""
        messages = [
            {"role": "system", "content": "Important system prompt that should be kept"},
            {"role": "user", "content": "a" * 400},  # 100 tokens
            {"role": "assistant", "content": "b" * 400},  # 100 tokens
            {"role": "user", "content": "c" * 400},  # 100 tokens
        ]
        
        result = token_manager.truncate_messages(messages, max_tokens=150)
        
        # System message should be preserved
        assert result[0]["role"] == "system"
        # Should have fewer messages
        assert len(result) < len(messages)
    
    def test_truncate_messages_keeps_recent(self, token_manager):
        """Test that recent messages are prioritized."""
        messages = [
            {"role": "user", "content": "Old message 1"},
            {"role": "user", "content": "Old message 2"},
            {"role": "user", "content": "Recent message"},
        ]
        
        result = token_manager.truncate_messages(messages, max_tokens=20)
        
        # Recent message should be included
        contents = [m["content"] for m in result]
        assert "Recent message" in contents
    
    def test_truncate_messages_empty_list(self, token_manager):
        """Test truncation with empty message list."""
        result = token_manager.truncate_messages([], max_tokens=100)
        assert result == []
    
    def test_different_chars_per_token(self):
        """Test token manager with different chars per token."""
        manager = TokenManager(chars_per_token=3)
        text = "Hello world"  # 11 characters
        tokens = manager.estimate_tokens(text)
        assert tokens == 3  # 11 // 3 = 3


class TestContextWindowManager:
    """Test cases for ContextWindowManager."""
    
    @pytest.fixture
    def context_manager(self):
        """Create context window manager."""
        token_manager = TokenManager(chars_per_token=4)
        return ContextWindowManager(token_manager)
    
    def test_build_context_with_all_components(self, context_manager):
        """Test building context with all components."""
        system_prompt = "You are helpful"
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        memories = ["User likes Python"]
        tools = ["search: Searches the web"]
        
        result = context_manager.build_context(
            system_prompt=system_prompt,
            conversation_history=history,
            retrieved_memories=memories,
            tool_descriptions=tools,
            max_tokens=500
        )
        
        # Should have at least 4 messages (system + history + memories + tools)
        assert len(result) >= 4
        
        # Check structure
        assert result[0]["role"] == "system"
        assert "You are helpful" in result[0]["content"]
    
    def test_build_context_without_optional_components(self, context_manager):
        """Test building context without memories or tools."""
        result = context_manager.build_context(
            system_prompt="System",
            conversation_history=[{"role": "user", "content": "Hello"}],
            retrieved_memories=[],
            tool_descriptions=[],
            max_tokens=100
        )
        
        # Should have system + history only
        assert len(result) >= 2
    
    def test_build_context_truncates_to_fit(self, context_manager):
        """Test that context is truncated to fit max_tokens."""
        # Create messages that would exceed the limit
        history = [{"role": "user", "content": "x" * 1000} for _ in range(20)]
        
        result = context_manager.build_context(
            system_prompt="System",
            conversation_history=history,
            retrieved_memories=[],
            tool_descriptions=[],
            max_tokens=50
        )
        
        # Should fit within limit
        total_tokens = context_manager.token_manager.estimate_messages_tokens(result)
        assert total_tokens <= 50