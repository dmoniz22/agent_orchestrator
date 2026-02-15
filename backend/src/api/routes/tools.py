"""Tool execution endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.skills.registry import get_tool_registry

logger = get_logger(__name__)
router = APIRouter()


class ToolInfo(BaseModel):
    """Tool information response."""
    
    tool_id: str
    name: str
    description: str
    danger_level: str


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""
    
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


@router.get("/", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    """List all available tools.
    
    Returns:
        List of tool information.
    """
    registry = get_tool_registry()
    tools = registry.list_tools()
    
    return [
        ToolInfo(
            tool_id=tool["tool_id"],
            name=tool.get("name", "Unknown"),
            description=tool.get("description", ""),
            danger_level=tool.get("danger_level", "safe")
        )
        for tool in tools
    ]


@router.get("/{tool_id}/schema")
async def get_tool_schema(tool_id: str) -> dict:
    """Get tool schema for LLM function calling.
    
    Args:
        tool_id: Tool identifier.
        
    Returns:
        Tool JSON schema.
        
    Raises:
        HTTPException: If tool not found.
    """
    registry = get_tool_registry()
    tool = registry.get_tool(tool_id)
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_id}"
        )
    
    schema = tool.get_schema()
    return schema.to_json_schema()


@router.post("/{tool_id}/execute")
async def execute_tool(tool_id: str, request: ToolExecuteRequest) -> dict:
    """Execute a tool.
    
    Args:
        tool_id: Tool identifier.
        request: Tool execution request with parameters.
        
    Returns:
        Tool execution result.
        
    Raises:
        HTTPException: If tool not found or execution fails.
    """
    registry = get_tool_registry()
    
    try:
        result = await registry.execute(tool_id, **request.parameters)
        return result
    except Exception as e:
        logger.error(f"Tool execution failed: {tool_id}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )
