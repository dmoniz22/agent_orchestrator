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
    session_id: str | None = Field(default=None, description="Session identifier")
    workflow: WorkflowConfig | None = Field(
        default=None, description="Optional workflow configuration"
    )
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
    # Use session_id as-is if provided, otherwise generate new UUID
    if request.session_id:
        session_id_str = request.session_id
    else:
        session_id_str = str(uuid4())

    logger.info("Executing task", session_id=session_id_str[:50], query=request.query[:100])

    try:
        # Use singleton orchestration engine with orchestrator agent configured
        engine = await get_orchestration_engine()

        # Convert string session ID to deterministic UUID
        # This ensures consistent session tracking across requests
        try:
            session_uuid = UUID(session_id_str)
        except ValueError:
            # Create deterministic UUID using MD5 hash with namespace
            import hashlib

            namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
            hash_input = namespace.bytes + session_id_str.encode("utf-8")
            session_uuid = UUID(bytes=hashlib.md5(hash_input).digest())

        result = await engine.run(query=request.query, session_id=session_uuid)

        return TaskResponse(
            task_id=UUID(result.get("task_id", str(uuid4()))),
            status=result.get("status", "completed"),
            response=result.get("response", ""),
            trace=result.get("trace"),
            steps_taken=result.get("steps_taken", 0),
            agents_invoked=result.get("agents_invoked", []),
            tools_used=result.get("tools_used", []),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error("Task execution failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {str(e)}",
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
        "message": "Task status tracking not yet implemented",
    }
