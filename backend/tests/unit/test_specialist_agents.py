"""Tests for specialist agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.specialists.orchestrator import OrchestratorAgent
from src.agents.specialists.coder import CoderAgent
from src.agents.specialists.researcher import ResearcherAgent
from src.agents.specialists.writer import WriterAgent
from src.agents.specialists.social import SocialAgent
from src.agents.base import AgentConfig
from src.models.provider import ModelResponse


class TestSpecialistAgents:
    """Test cases for all specialist agents."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock model provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value=ModelResponse(
            content='{"reasoning": "Test", "action": "final_response", "input": "Test response", "is_complete": true}',
            role="assistant",
            model="llama3.1:8b"
        ))
        return provider
    
    @pytest.fixture
    def mock_provider_text(self):
        """Create mock provider that returns plain text."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value=ModelResponse(
            content="This is a test response",
            role="assistant",
            model="llama3.1:8b"
        ))
        return provider
    
    @pytest.mark.asyncio
    async def test_orchestrator_agent(self, mock_provider):
        """Test OrchestratorAgent."""
        config = AgentConfig(
            name="Orchestrator",
            description="Routes decisions",
            temperature=0.1
        )
        agent = OrchestratorAgent(
            agent_id="orchestrator",
            config=config,
            model_provider=mock_provider
        )
        
        result = await agent.run("Analyze this query")
        
        assert isinstance(result, dict)
        assert "action" in result
        assert "is_complete" in result
        mock_provider.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrator_parse_decision(self, mock_provider):
        """Test orchestrator decision parsing."""
        config = AgentConfig(name="Orchestrator", description="Test")
        agent = OrchestratorAgent(
            agent_id="orchestrator",
            config=config,
            model_provider=mock_provider
        )
        
        # Test JSON parsing from markdown
        decision = agent._parse_decision('```json\n{"action": "call_agent", "agent_id": "coder"}\n```')
        assert decision["action"] == "call_agent"
        assert decision["agent_id"] == "coder"
        
        # Test plain text fallback
        decision = agent._parse_decision("Just a text response")
        assert decision["action"] == "final_response"
        assert decision["is_complete"] is True
    
    @pytest.mark.asyncio
    async def test_coder_agent(self, mock_provider_text):
        """Test CoderAgent."""
        config = AgentConfig(
            name="Coder",
            description="Code specialist",
            temperature=0.2
        )
        agent = CoderAgent(
            agent_id="coder",
            config=config,
            model_provider=mock_provider_text
        )
        
        result = await agent.run("Write a Python function")
        
        assert isinstance(result, str)
        assert "test response" in result
        mock_provider_text.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_coder_agent_with_context(self, mock_provider_text):
        """Test CoderAgent with context."""
        config = AgentConfig(name="Coder", description="Test")
        agent = CoderAgent(
            agent_id="coder",
            config=config,
            model_provider=mock_provider_text
        )
        
        context = {
            "language": "python",
            "existing_code": "def old_func(): pass"
        }
        
        result = await agent.run("Refactor this code", context=context)
        
        assert isinstance(result, str)
        # Verify context was used in prompt building
        call_args = mock_provider_text.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get('messages', [])
        assert any("python" in str(msg.content).lower() for msg in prompt)
    
    @pytest.mark.asyncio
    async def test_researcher_agent(self, mock_provider_text):
        """Test ResearcherAgent."""
        config = AgentConfig(
            name="Researcher",
            description="Research specialist"
        )
        agent = ResearcherAgent(
            agent_id="researcher",
            config=config,
            model_provider=mock_provider_text
        )
        
        result = await agent.run("Research Python async patterns")
        
        assert isinstance(result, str)
        assert "test response" in result
    
    @pytest.mark.asyncio
    async def test_researcher_agent_with_search_results(self, mock_provider_text):
        """Test ResearcherAgent with search context."""
        config = AgentConfig(name="Researcher", description="Test")
        agent = ResearcherAgent(
            agent_id="researcher",
            config=config,
            model_provider=mock_provider_text
        )
        
        context = {
            "search_results": [
                {"title": "Async in Python", "snippet": "Asyncio is great"}
            ]
        }
        
        result = await agent.run("Tell me about async", context=context)
        
        assert isinstance(result, str)
        # Verify search results were included in prompt
        call_args = mock_provider_text.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get('messages', [])
        prompt_text = " ".join([str(msg.content) for msg in prompt])
        assert "Async in Python" in prompt_text or "search" in prompt_text.lower()
    
    @pytest.mark.asyncio
    async def test_writer_agent(self, mock_provider_text):
        """Test WriterAgent."""
        config = AgentConfig(
            name="Writer",
            description="Content writer",
            temperature=0.7
        )
        agent = WriterAgent(
            agent_id="writer",
            config=config,
            model_provider=mock_provider_text
        )
        
        result = await agent.run("Write a blog post about AI")
        
        assert isinstance(result, str)
        assert "test response" in result
    
    @pytest.mark.asyncio
    async def test_writer_agent_with_style(self, mock_provider_text):
        """Test WriterAgent with style context."""
        config = AgentConfig(name="Writer", description="Test")
        agent = WriterAgent(
            agent_id="writer",
            config=config,
            model_provider=mock_provider_text
        )
        
        context = {
            "tone": "professional",
            "audience": "developers",
            "content_type": "technical blog"
        }
        
        result = await agent.run("Write about Python", context=context)
        
        assert isinstance(result, str)
        # Verify context was used
        call_args = mock_provider_text.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get('messages', [])
        prompt_text = " ".join([str(msg.content) for msg in prompt])
        assert "developers" in prompt_text or "professional" in prompt_text
    
    @pytest.mark.asyncio
    async def test_social_agent(self, mock_provider_text):
        """Test SocialAgent."""
        config = AgentConfig(
            name="Social",
            description="Social media specialist"
        )
        agent = SocialAgent(
            agent_id="social",
            config=config,
            model_provider=mock_provider_text
        )
        
        result = await agent.run("Create a tweet about our launch")
        
        assert isinstance(result, str)
        assert "test response" in result
    
    @pytest.mark.asyncio
    async def test_social_agent_with_platform(self, mock_provider_text):
        """Test SocialAgent with platform context."""
        config = AgentConfig(name="Social", description="Test")
        agent = SocialAgent(
            agent_id="social",
            config=config,
            model_provider=mock_provider_text
        )
        
        context = {
            "platform": "twitter",
            "char_limit": 280,
            "hashtags": ["#AI", "#Tech"]
        }
        
        result = await agent.run("Announce our product", context=context)
        
        assert isinstance(result, str)
        # Verify platform context was used
        call_args = mock_provider_text.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get('messages', [])
        prompt_text = " ".join([str(msg.content) for msg in prompt])
        assert "twitter" in prompt_text.lower() or "280" in prompt_text