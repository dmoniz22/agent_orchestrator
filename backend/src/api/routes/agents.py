"""Agent management endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.agents.registry import get_agent_registry
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class AgentInfo(BaseModel):
    """Agent information response."""
    
    agent_id: str
    name: str
    description: str
    model: str
    allowed_tools: list[str] = Field(default_factory=list)


@router.get("/", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    """List all available agents.
    
    Returns:
        List of agent information.
    """
    registry = get_agent_registry()
    agents = registry.list_agents()
    
    return [
        AgentInfo(
            agent_id=agent["agent_id"],
            name=agent.get("name", "Unknown"),
            description=agent.get("description", ""),
            model=agent.get("model", "default"),
            allowed_tools=agent.get("allowed_tools", [])
        )
        for agent in agents
    ]


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str) -> AgentInfo:
    """Get specific agent information.
    
    Args:
        agent_id: Agent identifier.
        
    Returns:
        Agent information.
        
    Raises:
        HTTPException: If agent not found.
    """
    registry = get_agent_registry()
    agent = registry.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}"
        )
    
    info = agent.get_info()
    return AgentInfo(
        agent_id=info["agent_id"],
        name=info["name"],
        description=info.get("description", ""),
        model=info.get("model", "default"),
        allowed_tools=info.get("allowed_tools", [])
    )


@router.post("/{agent_id}/run")
async def run_agent(agent_id: str, input_text: str) -> dict:
    """Run a specific agent directly.
    
    Args:
        agent_id: Agent identifier.
        input_text: Input for the agent.
        
    Returns:
        Agent response.
        
    Raises:
        HTTPException: If agent not found or execution fails.
    """
    registry = get_agent_registry()
    agent = registry.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}"
        )
    
    try:
        result = await agent.run(input_text)
        return {
            "agent_id": agent_id,
            "input": input_text,
            "output": result
        }
    except Exception as e:
        logger.error(f"Agent execution failed: {agent_id}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )
