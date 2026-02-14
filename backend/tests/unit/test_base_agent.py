"""Tests for BaseAgent class."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.base import AgentConfig, BaseAgent
from src.models.provider import Message, ModelResponse


class TestAgent(BaseAgent):
    """Concrete test agent implementation."""
    
    async def run(self, input_text: str, context=None):
        messages = self.build_messages(
            self.config.system_prompt,
            input_text
        )
        response = await self.generate(messages)
        return response.content


class TestBaseAgent:
    """Test cases for BaseAgent."""
    
    @pytest.fixture
    def config(self):
        """Create test agent configuration."""
        return AgentConfig(
            name="TestAgent",
            description="A test agent",
            model="llama3.1:8b",
            temperature=0.5,
            max_tokens=1024,
            system_prompt="You are a test agent",
            allowed_tools=["search", "read_file"]
        )
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock model provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value=ModelResponse(
            content="Test response",
            role="assistant",
            model="llama3.1:8b"
        ))
        return provider
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, config, mock_provider):
        """Test agent initialization."""
        agent = TestAgent(
            agent_id="test-agent",
            config=config,
            model_provider=mock_provider
        )
        
        assert agent.agent_id == "test-agent"
        assert agent.config.name == "TestAgent"
        assert agent.config.model == "llama3.1:8b"
    
    @pytest.mark.asyncio
    async def test_generate_response(self, config, mock_provider):
        """Test response generation."""
        agent = TestAgent(
            agent_id="test-agent",
            config=config,
            model_provider=mock_provider
        )
        
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello")
        ]
        
        response = await agent.generate(messages)
        
        assert response.content == "Test response"
        mock_provider.generate.assert_called_once()
    
    def test_render_prompt(self, config, mock_provider):
        """Test prompt template rendering."""
        agent = TestAgent(
            agent_id="test-agent",
            config=config,
            model_provider=mock_provider
        )
        
        template = "Hello {name}, you are {age} years old"
        variables = {"name": "Alice", "age": 30}
        
        result = agent.render_prompt(template, variables)
        assert result == "Hello Alice, you are 30 years old"
    
    def test_build_messages(self, config, mock_provider):
        """Test message building."""
        agent = TestAgent(
            agent_id="test-agent",
            config=config,
            model_provider=mock_provider
        )
        
        messages = agent.build_messages(
            system_prompt="System instruction",
            user_input="User query"
        )
        
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[0].content == "System instruction"
        assert messages[1].role == "user"
        assert messages[1].content == "User query"
    
    def test_can_use_tool_allowed(self, config, mock_provider):
        """Test tool permission check for allowed tool."""
        agent = TestAgent(
            agent_id="test-agent",
            config=config,
            model_provider=mock_provider
        )
        
        assert agent.can_use_tool("search") is True
        assert agent.can_use_tool("read_file") is True
    
    def test_can_use_tool_not_allowed(self, config, mock_provider):
        """Test tool permission check for disallowed tool."""
        agent = TestAgent(
            agent_id="test-agent",
            config=config,
            model_provider=mock_provider
        )
        
        assert agent.can_use_tool("delete_file") is False
    
    def test_can_use_tool_no_restrictions(self, mock_provider):
        """Test tool permission with no restrictions."""
        config = AgentConfig(
            name="OpenAgent",
            description="Agent with no tool restrictions"
        )
        
        agent = TestAgent(
            agent_id="open-agent",
            config=config,
            model_provider=mock_provider
        )
        
        assert agent.can_use_tool("any_tool") is True
    
    def test_get_info(self, config, mock_provider):
        """Test agent info retrieval."""
        agent = TestAgent(
            agent_id="test-agent",
            config=config,
            model_provider=mock_provider
        )
        
        info = agent.get_info()
        
        assert info["agent_id"] == "test-agent"
        assert info["name"] == "TestAgent"
        assert info["model"] == "llama3.1:8b"
        assert "search" in info["allowed_tools"]
