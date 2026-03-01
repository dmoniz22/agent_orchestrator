"""Pydantic schemas for orchestration."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskStatus(str, PyEnum):
    """Task execution status states."""
    
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_INPUT = "waiting_input"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionType(str, PyEnum):
    """Type of step action."""
    
    AGENT_CALL = "call_agent"
    TOOL_CALL = "use_tool"
    FINAL_RESPONSE = "final_response"


class AgentInfo(BaseModel):
    """Information about an available agent."""
    
    model_config = ConfigDict(from_attributes=True)
    
    agent_id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent display name")
    description: str = Field(..., description="Agent description")
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Tools this agent can use"
    )


class ToolInfo(BaseModel):
    """Information about an available tool."""
    
    model_config = ConfigDict(from_attributes=True)
    
    tool_id: str = Field(..., description="Tool identifier")
    name: str = Field(..., description="Tool display name")
    description: str = Field(..., description="Tool description")
    danger_level: str = Field(default="safe", description="Tool danger level")


class StepRecord(BaseModel):
    """Record of a single step in execution."""
    
    model_config = ConfigDict(from_attributes=True)
    
    step_id: UUID = Field(default_factory=uuid4, description="Unique step identifier")
    step_number: int = Field(..., description="Sequential step number")
    action_type: ActionType = Field(..., description="Type of action")
    actor_id: str = Field(..., description="Agent or tool that was invoked")
    input: str = Field(..., description="Input provided to actor")
    output: str | None = Field(default=None, description="Output returned by actor")
    duration_ms: int | None = Field(default=None, description="Execution time in milliseconds")
    success: bool = Field(default=True, description="Whether step succeeded")
    error: str | None = Field(default=None, description="Error details if failed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When step was executed"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class OrchestratorDecision(BaseModel):
    """Structured output from Orchestrator Agent.
    
    This is the JSON output that the orchestrator produces
    to decide the next step in task execution.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    reasoning: str = Field(..., description="Orchestrator's chain-of-thought")
    action: ActionType = Field(..., description="Action to take")
    agent_id: str | None = Field(
        default=None,
        description="Agent to call (if action is call_agent)"
    )
    tool_id: str | None = Field(
        default=None,
        description="Tool to use (if action is use_tool)"
    )
    tool_parameters: dict[str, Any] | None = Field(
        default=None,
        description="Tool parameters (if action is use_tool)"
    )
    input: str = Field(..., description="Input to pass to agent or tool")
    is_complete: bool = Field(
        default=False,
        description="Whether task is complete"
    )
    
    @field_validator("action")
    @classmethod
    def validate_action(cls, v: ActionType) -> ActionType:
        """Validate action is valid."""
        if v not in [ActionType.AGENT_CALL, ActionType.TOOL_CALL, ActionType.FINAL_RESPONSE]:
            raise ValueError(f"Invalid action: {v}")
        return v


class ExecutionState(BaseModel):
    """Central execution state that flows through the system.
    
    This is the primary data structure that tracks the progress
    of task execution through the orchestration system.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    task_id: UUID = Field(default_factory=uuid4, description="Unique task identifier")
    session_id: UUID = Field(..., description="User session identifier")
    original_query: str = Field(..., description="User's original input")
    current_objective: str | None = Field(
        default=None,
        description="Current objective (may evolve)"
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current execution status"
    )
    history: list[StepRecord] = Field(
        default_factory=list,
        description="Ordered list of all steps"
    )
    partial_results: list[str] = Field(
        default_factory=list,
        description="Intermediate outputs from sub-tasks"
    )
    available_agents: list[AgentInfo] = Field(
        default_factory=list,
        description="Available agents"
    )
    available_tools: list[ToolInfo] = Field(
        default_factory=list,
        description="Available tools"
    )
    step_count: int = Field(default=0, description="Current step number")
    max_steps: int = Field(default=10, description="Maximum steps allowed")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last modification time"
    )
    error: str | None = Field(default=None, description="Error if status is FAILED")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    conversation_history: list = Field(
        default_factory=list,
        description="Previous conversation turns for context"
    )
    
    def add_step(self, step: StepRecord) -> None:
        """Add a step to history and increment step count.
        
        Args:
            step: Step record to add.
        """
        self.history.append(step)
        self.step_count += 1
        self.updated_at = datetime.utcnow()
    
    def add_partial_result(self, result: str) -> None:
        """Add a partial result.
        
        Args:
            result: Result text to add.
        """
        self.partial_results.append(result)
        self.updated_at = datetime.utcnow()
    
    def get_last_step(self) -> StepRecord | None:
        """Get the most recent step.
        
        Returns:
            Last step record or None if no steps.
        """
        return self.history[-1] if self.history else None
    
    def is_complete(self) -> bool:
        """Check if execution is complete.
        
        Returns:
            True if status is COMPLETED or FAILED.
        """
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
    
    def has_exceeded_steps(self) -> bool:
        """Check if step limit has been exceeded.
        
        Returns:
            True if step_count >= max_steps.
        """
        return self.step_count >= self.max_steps


class ExecutionSummary(BaseModel):
    """Summary of task execution."""
    
    model_config = ConfigDict(from_attributes=True)
    
    task_id: UUID = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Final status")
    duration_seconds: float = Field(..., description="Total execution time")
    steps_taken: int = Field(..., description="Number of steps executed")
    agents_invoked: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    error: str | None = Field(default=None)


class WorkflowConfig(BaseModel):
    """Configuration for a workflow execution."""
    
    model_config = ConfigDict(from_attributes=True)
    
    workflow_type: str = Field(
        ...,
        description="Type: sequential, concurrent, hierarchical, group_chat, cyclic"
    )
    agents: list[str] = Field(..., description="Agent IDs to use")
    max_iterations: int = Field(default=10, description="Max iterations for cyclic")
    convergence_threshold: float | None = Field(
        default=None,
        description="Convergence threshold for cyclic"
    )