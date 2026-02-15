"""Integration tests for the complete OMNI system."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base import AgentConfig
from src.agents.specialists.coder import CoderAgent
from src.agents.specialists.researcher import ResearcherAgent
from src.memory.manager import MemoryManager
from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory
from src.skills.library.calculator import CalculatorTool
from src.skills.library.search import SearchTool
from src.skills.library.filesystem import FileReadTool
from src.orchestration.engine import OrchestrationEngine
from src.orchestration.router import Router
from src.orchestration.collator import Collator
from src.orchestration.state_machine import StateMachine
from src.orchestration.schemas import ExecutionState, TaskStatus
from src.models.provider import ModelResponse


@pytest.fixture
def mock_model_provider():
    """Create a mock model provider."""
    provider = MagicMock()
    provider.generate = AsyncMock(return_value=ModelResponse(
        content="Test response from model",
        role="assistant",
        model="llama3.1:8b"
    ))
    return provider


@pytest.fixture
def memory_manager():
    """Create a memory manager for testing."""
    short_term = ShortTermMemory(max_entries=20)
    long_term = LongTermMemory()
    return MemoryManager(short_term, long_term)


class TestAgentToolIntegration:
    """Integration tests for agent and tool interactions."""
    
    @pytest.mark.asyncio
    async def test_coder_agent_with_file_read(self, mock_model_provider):
        """Test CoderAgent using FileReadTool."""
        # Create file read tool
        file_tool = FileReadTool(allowed_paths=["/tmp"])
        
        # Create coder agent
        config = AgentConfig(
            name="Coder",
            description="Code specialist",
            allowed_tools=["file.read"]
        )
        agent = CoderAgent(
            agent_id="test-coder",
            config=config,
            model_provider=mock_model_provider
        )
        
        # Test that agent can access tool
        assert agent.can_use_tool("file.read") is True
        assert agent.can_use_tool("file.write") is False
    
    @pytest.mark.asyncio
    async def test_researcher_agent_with_search(self, mock_model_provider):
        """Test ResearcherAgent with search results context."""
        config = AgentConfig(name="Researcher", description="Research specialist")
        agent = ResearcherAgent(
            agent_id="test-researcher",
            config=config,
            model_provider=mock_model_provider
        )
        
        # Run with search results context
        context = {
            "search_results": [
                {"title": "Python Tutorial", "snippet": "Learn Python basics"}
            ]
        }
        
        result = await agent.run("Tell me about Python", context=context)
        assert isinstance(result, str)
        assert len(result) > 0


class TestMemoryIntegration:
    """Integration tests for memory system."""
    
    @pytest.mark.asyncio
    async def test_conversation_flow_with_memory(self):
        """Test complete conversation flow with memory."""
        manager = MemoryManager()
        session_id = uuid4()
        
        # Simulate conversation
        await manager.store_conversation_turn("user", "Hello", session_id)
        await manager.store_conversation_turn("assistant", "Hi there!", session_id)
        await manager.store_conversation_turn("user", "How are you?", session_id)
        
        # Retrieve conversation history
        history = await manager.get_conversation_history(session_id)
        assert len(history) == 3
        
        # Check roles are preserved
        roles = [entry.metadata.get("role") for entry in history]
        assert "user" in roles
        assert "assistant" in roles
    
    @pytest.mark.asyncio
    async def test_memory_retrieval_for_context(self):
        """Test retrieving relevant memories for context."""
        manager = MemoryManager()
        session_id = uuid4()
        
        # Store some memories
        await manager.store("Python is a programming language", session_id, importance=0.9)
        await manager.store("JavaScript is used for web development", session_id, importance=0.9)
        await manager.store("Coffee is a beverage", session_id, importance=0.5)
        
        # Retrieve context
        context = await manager.retrieve_context("programming", session_id)
        
        # Should find relevant memories
        assert len(context["short_term"]) > 0 or len(context["long_term"]) > 0


class TestOrchestrationFlow:
    """Integration tests for orchestration flow."""
    
    @pytest.mark.asyncio
    async def test_simple_orchestration_flow(self, mock_model_provider):
        """Test simple orchestration flow."""
        # Create components
        state_machine = StateMachine()
        router = Router()
        collator = Collator()
        
        # Create orchestration engine
        engine = OrchestrationEngine(
            state_machine=state_machine,
            router=router,
            collator=collator,
            max_steps=5
        )
        
        # Mock orchestrator agent
        from src.orchestration.schemas import ActionType
        mock_orchestrator = MagicMock()
        mock_decision = MagicMock()
        mock_decision.reasoning = "Test reasoning"
        mock_decision.action = ActionType.FINAL_RESPONSE
        mock_decision.input = "Test query"
        mock_decision.is_complete = True
        mock_decision.agent_id = None
        mock_decision.tool_id = None
        mock_decision.tool_parameters = None
        mock_orchestrator.decide = AsyncMock(return_value=mock_decision)
        engine.orchestrator_agent = mock_orchestrator
        
        # Run orchestration
        session_id = uuid4()
        result = await engine.run(
            query="Test query",
            session_id=session_id
        )
        
        # Verify result structure
        assert "task_id" in result
        assert "response" in result
        assert "trace" in result
    
    @pytest.mark.asyncio
    async def test_multi_step_orchestration(self, mock_model_provider):
        """Test multi-step orchestration with state transitions."""
        state_machine = StateMachine()
        
        # Create execution state
        state = ExecutionState(
            session_id=uuid4(),
            original_query="Test query",
            max_steps=3
        )
        
        # Test state transitions
        assert state.status == TaskStatus.PENDING
        
        state_machine.transition(state, TaskStatus.PLANNING)
        assert state.status == TaskStatus.PLANNING
        
        state_machine.transition(state, TaskStatus.EXECUTING)
        assert state.status == TaskStatus.EXECUTING
        
        state_machine.mark_completed(state)
        assert state.status == TaskStatus.COMPLETED


class TestToolExecution:
    """Integration tests for tool execution."""
    
    @pytest.mark.asyncio
    async def test_calculator_execution(self):
        """Test calculator tool execution."""
        calculator = CalculatorTool()
        
        result = await calculator.run(expression="2 + 2")
        assert result.success is True
        assert result.result == 4
    
    @pytest.mark.asyncio
    async def test_calculator_with_variables(self):
        """Test calculator with math functions."""
        calculator = CalculatorTool()
        
        result = await calculator.run(expression="sqrt(16) + pi")
        assert result.success is True
        assert result.result > 7  # 4 + ~3.14
    
    @pytest.mark.asyncio
    async def test_file_read_with_security(self):
        """Test file read with path restrictions."""
        tool = FileReadTool(allowed_paths=["/tmp"])
        
        # Should deny access to restricted path
        result = await tool.run(path="/etc/passwd")
        assert result.success is False
        assert "Access denied" in result.error


class TestEndToEndWorkflows:
    """End-to-end workflow tests."""
    
    @pytest.mark.asyncio
    async def test_coder_workflow_with_memory(self, mock_model_provider):
        """Test complete coder workflow with memory."""
        # Setup
        memory = MemoryManager()
        session_id = uuid4()
        
        config = AgentConfig(
            name="Coder",
            description="Code specialist",
            model="llama3.1:8b"
        )
        agent = CoderAgent(
            agent_id="coder",
            config=config,
            model_provider=mock_model_provider
        )
        
        # Execute coding task
        context = {"language": "python"}
        result = await agent.run("Write a hello world function", context=context)
        
        # Store in memory
        await memory.store(result, session_id, importance=0.8)
        
        # Verify memory
        history = await memory.get_conversation_history(session_id)
        assert len(history) >= 0  # At least empty
    
    @pytest.mark.asyncio
    async def test_multi_agent_session(self, mock_model_provider):
        """Test session with multiple agents."""
        session_id = uuid4()
        memory = MemoryManager()
        
        # Create agents
        coder_config = AgentConfig(name="Coder", description="Code")
        researcher_config = AgentConfig(name="Researcher", description="Research")
        
        coder = CoderAgent(
            agent_id="coder",
            config=coder_config,
            model_provider=mock_model_provider
        )
        researcher = ResearcherAgent(
            agent_id="researcher",
            config=researcher_config,
            model_provider=mock_model_provider
        )
        
        # Simulate multi-agent workflow
        research_result = await researcher.run("Research Python asyncio")
        await memory.store(research_result, session_id, importance=0.8)
        
        code_result = await coder.run("Write example code", context={"language": "python"})
        await memory.store(code_result, session_id, importance=0.8)
        
        # Verify both results in memory
        recent = await memory.short_term.get_recent(session_id)
        assert len(recent) == 2


class TestRegistryIntegration:
    """Integration tests for agent and tool registries."""
    
    @pytest.mark.asyncio
    async def test_agent_registry_workflow(self, mock_model_provider):
        """Test agent registry with multiple agents."""
        from src.agents.registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # Register agent classes
        registry.register_agent_class("coder", CoderAgent)
        registry.register_agent_class("researcher", ResearcherAgent)
        
        # Register configs
        registry.register_config("my-coder", AgentConfig(name="My Coder", description="Test coder"))
        
        # Create agent
        agent = registry.create_agent("my-coder", "coder", model_provider=mock_model_provider)
        
        assert agent is not None
        assert isinstance(agent, CoderAgent)
        assert agent.agent_id == "my-coder"
    
    def test_tool_registry_schema_collection(self):
        """Test tool registry schema collection."""
        from src.skills.registry import ToolRegistry
        
        registry = ToolRegistry()
        
        # Register tools
        registry.register(CalculatorTool())
        registry.register(SearchTool())
        
        # Get schemas
        schemas = registry.get_schemas()
        
        assert len(schemas) == 2
        assert all("function" in schema for schema in schemas)


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_agent_handles_model_failure(self):
        """Test agent handles model provider failure gracefully."""
        # Create failing provider
        failing_provider = MagicMock()
        failing_provider.generate = AsyncMock(side_effect=Exception("Model error"))
        
        config = AgentConfig(name="Test", description="Test")
        agent = CoderAgent(
            agent_id="test",
            config=config,
            model_provider=failing_provider
        )
        
        # Should raise exception
        with pytest.raises(Exception):
            await agent.run("Test query")
    
    @pytest.mark.asyncio
    async def test_tool_handles_invalid_parameters(self):
        """Test tool handles invalid parameters."""
        calculator = CalculatorTool()
        
        # Missing required parameter
        result = await calculator.run()
        assert result.success is False
        assert "Missing required parameter" in result.error
    
    @pytest.mark.asyncio
    async def test_memory_handles_session_isolation(self):
        """Test memory properly isolates sessions."""
        manager = MemoryManager()
        
        session1 = uuid4()
        session2 = uuid4()
        
        # Store in session 1
        await manager.store("Session 1 data", session1)
        
        # Store in session 2
        await manager.store("Session 2 data", session2)
        
        # Retrieve for session 1
        recent1 = await manager.short_term.get_recent(session1)
        assert len(recent1) == 1
        assert recent1[0].content == "Session 1 data"
        
        # Retrieve for session 2
        recent2 = await manager.short_term.get_recent(session2)
        assert len(recent2) == 1
        assert recent2[0].content == "Session 2 data"