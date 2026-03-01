"""Task execution endpoints."""

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.orchestration.engine import get_orchestration_engine
from src.orchestration.schemas import WorkflowConfig

logger = get_logger(__name__)
router = APIRouter()


class TaskRequest(BaseModel):
    """Task execution request."""
    
    query: str = Field(..., description="User query or task description")
    session_id: UUID | None = Field(default=None, description="Session identifier")
    workflow: WorkflowConfig | None = Field(default=None, description="Optional workflow configuration")
    context: dict[str, Any] | None = Field(default=None, description="Additional context")


class TaskResponse(BaseModel):
    """Task execution response."""
    
    task_id: UUID
    status: str
    response: str
    trace: dict[str, Any] | None = None
    steps_taken: int = 0
    agents_invoked: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    error: str | None = None


@router.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest) -> TaskResponse:
    """Execute a task through the orchestration engine.
    
    Args:
        request: Task execution request.
        
    Returns:
        Task execution result.
    """
    session_id = request.session_id or uuid4()
    
    logger.info(
        "Executing task",
        session_id=str(session_id),
        query=request.query[:100]
    )
    
    try:
        # Use singleton orchestration engine with orchestrator agent configured
        engine = await get_orchestration_engine()
        
        result = await engine.run(
            query=request.query,
            session_id=session_id
        )
        
        return TaskResponse(
            task_id=UUID(result.get("task_id", str(uuid4()))),
            status=result.get("status", "completed"),
            response=result.get("response", ""),
            trace=result.get("trace"),
            steps_taken=result.get("steps_taken", 0),
            agents_invoked=result.get("agents_invoked", []),
            tools_used=result.get("tools_used", []),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error("Task execution failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {str(e)}"
        )


@router.get("/{task_id}/status")
async def get_task_status(task_id: UUID) -> dict:
    """Get task execution status.
    
    Args:
        task_id: Task identifier.
        
    Returns:
        Task status information.
    """
    # TODO: Implement task status tracking
    return {
        "task_id": str(task_id),
        "status": "not_implemented",
        "message": "Task status tracking not yet implemented"
    }
