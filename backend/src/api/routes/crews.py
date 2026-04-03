"""Crews API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class CrewInfo(BaseModel):
    """Crew information."""

    crew_id: str
    name: str
    description: str
    agents: list[str]
    status: str
    tasks_completed: int


class CrewsResponse(BaseModel):
    """Crews list response."""

    crews: list[CrewInfo]


# Define available crews based on the backend architecture
CREWS = [
    {
        "crew_id": "research",
        "name": "Research Crew",
        "description": "Web research and information synthesis",
        "agents": ["researcher"],
        "status": "active",
        "tasks_completed": 0,
    },
    {
        "crew_id": "coding",
        "name": "Coding Crew",
        "description": "Code generation, review, and analysis",
        "agents": ["coder"],
        "status": "active",
        "tasks_completed": 0,
    },
    {
        "crew_id": "writing",
        "name": "Writing Crew",
        "description": "Content creation and editing",
        "agents": ["writer"],
        "status": "active",
        "tasks_completed": 0,
    },
    {
        "crew_id": "social",
        "name": "Social Crew",
        "description": "Social media content creation",
        "agents": ["social"],
        "status": "active",
        "tasks_completed": 0,
    },
    {
        "crew_id": "orchestration",
        "name": "Orchestration Crew",
        "description": "Routes queries to appropriate specialists",
        "agents": ["orchestrator"],
        "status": "active",
        "tasks_completed": 0,
    },
]


@router.get("/crews", response_model=list[dict[str, Any]])
async def get_crews() -> list[dict[str, Any]]:
    """Get all crews.

    Returns:
        List of crew information.
    """
    return CREWS


@router.get("/crews/{crew_id}", response_model=dict[str, Any])
async def get_crew(crew_id: str) -> dict[str, Any]:
    """Get a specific crew.

    Args:
        crew_id: The crew identifier.

    Returns:
        Crew information.
    """
    for crew in CREWS:
        if crew["crew_id"] == crew_id:
            return crew
    raise HTTPException(status_code=404, detail="Crew not found")
