"""Tests for BaseTool and ToolRegistry."""

import pytest
from unittest.mock import AsyncMock

from src.skills.base import (
    BaseTool,
    ToolDangerLevel,
    ToolParameter,
    ToolResult,
    ToolSchema,
)
from src.skills.registry import ToolRegistry, get_tool_registry


class MockTool(BaseTool):
    """Concrete tool implementation for testing."""
    
    async def execute(self, query: str = "", count: int = 10) -> ToolResult:
        """Mock execution."""
        return ToolResult(
            success=True,
            result={"query": query, "count": count},
            metadata={"tool": self.tool_id}
        )
    
    def get_schema(self) -> ToolSchema:
        """Mock schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            danger_level=self.danger_level,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                ),
                ToolParameter(
                    name="count",
                    type="integer",
                    description="Number of results",
                    required=False,
                    default=10
                )
            ]
        )


class TestToolParameter:
    """Test cases for ToolParameter."""
    
    def test_tool_parameter_creation(self):
        """Test creating a tool parameter."""
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True
        )
        
        assert param.name == "query"
        assert param.type == "string"
        assert param.required is True
    
    def test_tool_parameter_optional(self):
        """Test optional parameter with default."""
        param = ToolParameter(
            name="limit",
            type="integer",
            description="Result limit",
            required=False,
            default=10
        )
        
        assert param.required is False
        assert param.default == 10


class TestToolSchema:
    """Test cases for ToolSchema."""
    
    def test_schema_to_json(self):
        """Test converting schema to JSON format."""
        schema = ToolSchema(
            name="search",
            description="Search the web",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Limit results",
                    required=False,
                    default=10
                )
            ]
        )
        
        json_schema = schema.to_json_schema()
        
        assert json_schema["type"] == "function"
        assert json_schema["function"]["name"] == "search"
        assert "query" in json_schema["function"]["parameters"]["properties"]
        assert "query" in json_schema["function"]["parameters"]["required"]
        assert "limit" not in json_schema["function"]["parameters"]["required"]


class TestBaseTool:
    """Test cases for BaseTool."""
    
    @pytest.fixture
    def tool(self):
        """Create a test tool."""
        return MockTool(
            tool_id="test-search",
            name="Test Search",
            description="A test search tool",
            danger_level=ToolDangerLevel.SAFE,
            timeout_seconds=5
        )
    
    def test_tool_initialization(self, tool):
        """Test tool initialization."""
        assert tool.tool_id == "test-search"
        assert tool.name == "Test Search"
        assert tool.danger_level == ToolDangerLevel.SAFE
        assert tool.timeout_seconds == 5
    
    @pytest.mark.asyncio
    async def test_tool_run_success(self, tool):
        """Test successful tool execution."""
        result = await tool.run(query="test", count=5)
        
        assert result.success is True
        assert result.result["query"] == "test"
        assert result.result["count"] == 5
        assert result.duration_ms is not None
    
    @pytest.mark.asyncio
    async def test_tool_run_missing_required_param(self, tool):
        """Test execution with missing required parameter."""
        result = await tool.run(count=5)  # Missing 'query'
        
        assert result.success is False
        assert "Missing required parameter" in result.error
    
    @pytest.mark.asyncio
    async def test_tool_run_unknown_param(self, tool):
        """Test execution with unknown parameter."""
        result = await tool.run(query="test", unknown_param=True)
        
        assert result.success is False
        assert "Unknown parameter" in result.error
    
    def test_tool_get_info(self, tool):
        """Test getting tool info."""
        info = tool.get_info()
        
        assert info["tool_id"] == "test-search"
        assert info["name"] == "Test Search"
        assert info["danger_level"] == "safe"


class TestToolRegistry:
    """Test cases for ToolRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        return ToolRegistry()
    
    @pytest.fixture
    def tool(self):
        """Create a test tool."""
        return MockTool(
            tool_id="test-tool",
            name="Test Tool",
            description="For testing"
        )
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ToolRegistry()
        assert registry._tools == {}
    
    def test_register_tool(self, registry, tool):
        """Test registering a tool."""
        registry.register(tool)
        
        assert "test-tool" in registry._tools
        assert registry._tools["test-tool"] == tool
    
    def test_get_tool_found(self, registry, tool):
        """Test getting existing tool."""
        registry.register(tool)
        
        result = registry.get_tool("test-tool")
        assert result == tool
    
    def test_get_tool_not_found(self, registry):
        """Test getting non-existent tool."""
        result = registry.get_tool("nonexistent")
        assert result is None
    
    def test_list_tools(self, registry, tool):
        """Test listing registered tools."""
        registry.register(tool)
        
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["tool_id"] == "test-tool"
    
    def test_get_schemas(self, registry, tool):
        """Test getting tool schemas."""
        registry.register(tool)
        
        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "Test Tool"
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, registry, tool):
        """Test executing a tool through registry."""
        registry.register(tool)
        
        result = await registry.execute("test-tool", query="test")
        
        assert result["success"] is True
        assert result["result"]["query"] == "test"
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, registry):
        """Test executing non-existent tool."""
        with pytest.raises(Exception) as exc_info:
            await registry.execute("nonexistent")
        
        assert "Tool not found" in str(exc_info.value)
    
    def test_unregister_existing(self, registry, tool):
        """Test unregistering existing tool."""
        registry.register(tool)
        
        result = registry.unregister("test-tool")
        
        assert result is True
        assert "test-tool" not in registry._tools
    
    def test_unregister_nonexistent(self, registry):
        """Test unregistering non-existent tool."""
        result = registry.unregister("nonexistent")
        assert result is False
    
    def test_get_tool_registry_singleton(self):
        """Test that get_tool_registry returns singleton."""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        
        assert registry1 is registry2
