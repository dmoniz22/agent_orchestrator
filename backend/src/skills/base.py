"""Base tool class for all skills/tools."""

from abc import ABC, abstractmethod
from typing import Any
from enum import Enum

from pydantic import BaseModel, Field

from src.core.exceptions import ToolExecutionError
from src.core.logging import get_logger

logger = get_logger(__name__)


class ToolDangerLevel(str, Enum):
    """Safety classification for tools."""
    
    SAFE = "safe"           # Read-only, no side effects
    NORMAL = "normal"       # Standard operations with validation
    DESTRUCTIVE = "destructive"  # Can modify/delete data


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, number, boolean, etc.)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Any = Field(default=None, description="Default value if optional")


class ToolSchema(BaseModel):
    """Schema definition for a tool."""
    
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    danger_level: ToolDangerLevel = Field(default=ToolDangerLevel.SAFE)
    parameters: list[ToolParameter] = Field(default_factory=list)
    
    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema format for LLM function calling."""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


class ToolResult(BaseModel):
    """Result of a tool execution."""
    
    success: bool = Field(..., description="Whether execution succeeded")
    result: Any = Field(default=None, description="Tool output")
    error: str | None = Field(default=None, description="Error message if failed")
    duration_ms: int | None = Field(default=None, description="Execution time")
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all tools.
    
    Provides common functionality for:
    - Tool metadata and schema
    - Parameter validation
    - Execution with error handling
    - Safety/danger level classification
    """
    
    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        danger_level: ToolDangerLevel = ToolDangerLevel.SAFE,
        timeout_seconds: int = 30
    ) -> None:
        """Initialize base tool.
        
        Args:
            tool_id: Unique tool identifier.
            name: Human-readable tool name.
            description: Tool description.
            danger_level: Safety classification.
            timeout_seconds: Execution timeout.
        """
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.danger_level = danger_level
        self.timeout_seconds = timeout_seconds
        
        logger.info(
            "Tool initialized",
            tool_id=tool_id,
            name=name,
            danger_level=danger_level.value
        )
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters.
            
        Returns:
            Tool execution result.
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Get tool schema for LLM function calling.
        
        Returns:
            Tool schema definition.
        """
        pass
    
    async def run(self, **kwargs: Any) -> ToolResult:
        """Run tool with validation and error handling.
        
        Args:
            **kwargs: Tool parameters.
            
        Returns:
            Tool result.
        """
        import asyncio
        import time
        
        start_time = time.time()
        
        logger.info(
            "Executing tool",
            tool_id=self.tool_id,
            params=list(kwargs.keys())
        )
        
        try:
            # Validate parameters
            self._validate_params(kwargs)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(**kwargs),
                timeout=self.timeout_seconds
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms
            
            logger.info(
                "Tool execution completed",
                tool_id=self.tool_id,
                success=result.success,
                duration_ms=duration_ms
            )
            
            return result
            
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Tool execution timeout",
                tool_id=self.tool_id,
                timeout=self.timeout_seconds
            )
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {self.timeout_seconds}s",
                duration_ms=duration_ms
            )
            
        except ToolExecutionError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Tool execution failed",
                tool_id=self.tool_id,
                error=str(e)
            )
            return ToolResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Unexpected tool error",
                tool_id=self.tool_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return ToolResult(
                success=False,
                error=f"Unexpected error: {e}",
                duration_ms=duration_ms
            )
    
    def _validate_params(self, params: dict[str, Any]) -> None:
        """Validate tool parameters against schema.
        
        Args:
            params: Parameters to validate.
            
        Raises:
            ToolExecutionError: If validation fails.
        """
        schema = self.get_schema()
        
        # Check required parameters
        for param in schema.parameters:
            if param.required and param.name not in params:
                raise ToolExecutionError(
                    message=f"Missing required parameter: {param.name}",
                    tool_id=self.tool_id
                )
        
        # Check for unknown parameters
        allowed = {p.name for p in schema.parameters}
        for key in params:
            if key not in allowed:
                raise ToolExecutionError(
                    message=f"Unknown parameter: {key}",
                    tool_id=self.tool_id
                )
    
    def get_info(self) -> dict[str, Any]:
        """Get tool information.
        
        Returns:
            Tool metadata.
        """
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "danger_level": self.danger_level.value,
            "timeout_seconds": self.timeout_seconds
        }
