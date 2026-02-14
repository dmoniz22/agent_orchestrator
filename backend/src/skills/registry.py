"""Tool registry for managing tool lifecycle and discovery."""

from typing import Any

from src.core.exceptions import ToolExecutionError
from src.core.logging import get_logger
from .base import BaseTool, ToolSchema

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for managing tool instances and discovery.
    
    Handles:
    - Tool registration
    - Tool discovery and listing
    - Tool execution
    """
    
    def __init__(self) -> None:
        """Initialize tool registry."""
        self._tools: dict[str, BaseTool] = {}
        logger.info("ToolRegistry initialized")
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool.
        
        Args:
            tool: Tool instance to register.
        """
        self._tools[tool.tool_id] = tool
        logger.info(
            "Tool registered",
            tool_id=tool.tool_id,
            name=tool.name
        )
    
    def get_tool(self, tool_id: str) -> BaseTool | None:
        """Get a tool by ID.
        
        Args:
            tool_id: Tool identifier.
            
        Returns:
            Tool instance or None if not found.
        """
        return self._tools.get(tool_id)
    
    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools.
        
        Returns:
            List of tool information dictionaries.
        """
        return [
            {
                "tool_id": tool_id,
                **tool.get_info()
            }
            for tool_id, tool in self._tools.items()
        ]
    
    def get_schemas(self) -> list[dict[str, Any]]:
        """Get all tool schemas for LLM function calling.
        
        Returns:
            List of tool schemas in JSON format.
        """
        schemas = []
        for tool in self._tools.values():
            try:
                schema = tool.get_schema()
                schemas.append(schema.to_json_schema())
            except Exception as e:
                logger.error(
                    "Failed to get tool schema",
                    tool_id=tool.tool_id,
                    error=str(e)
                )
        return schemas
    
    async def execute(
        self,
        tool_id: str,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Execute a tool by ID.
        
        Args:
            tool_id: Tool to execute.
            **kwargs: Tool parameters.
            
        Returns:
            Tool execution result as dictionary.
            
        Raises:
            ToolExecutionError: If tool not found.
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ToolExecutionError(
                message=f"Tool not found: {tool_id}",
                tool_id=tool_id
            )
        
        result = await tool.run(**kwargs)
        return result.model_dump()
    
    def unregister(self, tool_id: str) -> bool:
        """Unregister a tool.
        
        Args:
            tool_id: Tool identifier.
            
        Returns:
            True if tool was found and removed.
        """
        if tool_id in self._tools:
            del self._tools[tool_id]
            logger.info("Tool unregistered", tool_id=tool_id)
            return True
        return False


# Global registry instance
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get or create global tool registry.
    
    Returns:
        ToolRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
