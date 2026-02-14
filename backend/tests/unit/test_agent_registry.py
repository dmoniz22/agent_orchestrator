"""Tests for AgentRegistry."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import yaml

from src.agents.base import AgentConfig, BaseAgent
from src.agents.registry import AgentRegistry, get_agent_registry


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    async def run(self, input_text: str, context=None):
        return f"Mock response: {input_text}"


class TestAgentRegistry:
    """Test cases for AgentRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        return AgentRegistry()
    
    @pytest.fixture
    def sample_config(self):
        """Create sample agent config."""
        return AgentConfig(
            name="TestAgent",
            description="A test agent",
            model="llama3.1:8b"
        )
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = AgentRegistry()
        assert registry._agents == {}
        assert registry._configs == {}
        assert registry._agent_classes == {}
    
    def test_register_agent_class(self, registry):
        """Test registering agent class."""
        registry.register_agent_class("mock", MockAgent)
        assert "mock" in registry._agent_classes
        assert registry._agent_classes["mock"] == MockAgent
    
    def test_register_config(self, registry, sample_config):
        """Test registering agent config."""
        registry.register_config("test-agent", sample_config)
        assert "test-agent" in registry._configs
        assert registry._configs["test-agent"].name == "TestAgent"
    
    def test_register_agent(self, registry, sample_config):
        """Test registering agent instance."""
        agent = MockAgent(
            agent_id="test-agent",
            config=sample_config
        )
        registry.register_agent("test-agent", agent)
        assert "test-agent" in registry._agents
        assert registry._agents["test-agent"] == agent
    
    def test_get_agent_found(self, registry, sample_config):
        """Test getting existing agent."""
        agent = MockAgent(
            agent_id="test-agent",
            config=sample_config
        )
        registry.register_agent("test-agent", agent)
        
        result = registry.get_agent("test-agent")
        assert result == agent
    
    def test_get_agent_not_found(self, registry):
        """Test getting non-existent agent."""
        result = registry.get_agent("nonexistent")
        assert result is None
    
    def test_get_config_found(self, registry, sample_config):
        """Test getting existing config."""
        registry.register_config("test-agent", sample_config)
        
        result = registry.get_config("test-agent")
        assert result == sample_config
    
    def test_list_agents(self, registry, sample_config):
        """Test listing registered agents."""
        agent1 = MockAgent(agent_id="agent-1", config=sample_config)
        agent2 = MockAgent(agent_id="agent-2", config=sample_config)
        
        registry.register_agent("agent-1", agent1)
        registry.register_agent("agent-2", agent2)
        
        agents = registry.list_agents()
        assert len(agents) == 2
        agent_ids = [a["agent_id"] for a in agents]
        assert "agent-1" in agent_ids
        assert "agent-2" in agent_ids
    
    def test_list_configs(self, registry, sample_config):
        """Test listing registered configs."""
        registry.register_config("agent-1", sample_config)
        
        configs = registry.list_configs()
        assert len(configs) == 1
        assert configs[0]["agent_id"] == "agent-1"
        assert configs[0]["name"] == "TestAgent"
    
    def test_create_agent_success(self, registry, sample_config):
        """Test creating agent instance."""
        registry.register_agent_class("mock", MockAgent)
        registry.register_config("new-agent", sample_config)
        
        agent = registry.create_agent("new-agent", "mock")
        
        assert isinstance(agent, MockAgent)
        assert agent.agent_id == "new-agent"
        assert "new-agent" in registry._agents
    
    def test_create_agent_unknown_type(self, registry):
        """Test creating agent with unknown type."""
        with pytest.raises(Exception) as exc_info:
            registry.create_agent("test", "unknown")
        
        assert "Unknown agent type" in str(exc_info.value)
    
    def test_create_agent_with_override(self, registry, sample_config):
        """Test creating agent with config override."""
        registry.register_agent_class("mock", MockAgent)
        registry.register_config("test-agent", sample_config)
        
        overrides = {"temperature": 0.9, "max_tokens": 512}
        agent = registry.create_agent("test-agent", "mock", override_config=overrides)
        
        assert agent.config.temperature == 0.9
        assert agent.config.max_tokens == 512
        assert agent.config.name == "TestAgent"  # Original preserved
    
    def test_unregister_existing(self, registry, sample_config):
        """Test unregistering existing agent."""
        agent = MockAgent(agent_id="test-agent", config=sample_config)
        registry.register_agent("test-agent", agent)
        registry.register_config("test-agent", sample_config)
        
        result = registry.unregister("test-agent")
        
        assert result is True
        assert "test-agent" not in registry._agents
        assert "test-agent" not in registry._configs
    
    def test_unregister_nonexistent(self, registry):
        """Test unregistering non-existent agent."""
        result = registry.unregister("nonexistent")
        assert result is False
    
    def test_load_config_from_directory(self):
        """Test loading configs from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create a config file
            config_data = {
                "name": "FileAgent",
                "description": "Loaded from file",
                "model": "llama3.1:8b",
                "temperature": 0.7
            }
            
            config_file = config_dir / "file-agent.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            registry = AgentRegistry(config_dir)
            
            assert "file-agent" in registry._configs
            assert registry._configs["file-agent"].name == "FileAgent"
    
    def test_load_config_multiple_agents_per_file(self):
        """Test loading multiple agents from single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create a config file with multiple agents
            config_data = {
                "agents": [
                    {
                        "agent_id": "agent-1",
                        "name": "FirstAgent",
                        "description": "First agent"
                    },
                    {
                        "agent_id": "agent-2", 
                        "name": "SecondAgent",
                        "description": "Second agent"
                    }
                ]
            }
            
            config_file = config_dir / "multi-agent.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            registry = AgentRegistry(config_dir)
            
            assert "agent-1" in registry._configs
            assert "agent-2" in registry._configs
    
    def test_get_agent_registry_singleton(self):
        """Test that get_agent_registry returns singleton."""
        registry1 = get_agent_registry()
        registry2 = get_agent_registry()
        
        assert registry1 is registry2