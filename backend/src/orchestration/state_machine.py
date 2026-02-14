"""State machine for managing task execution status."""

from typing import Any

from ..core.exceptions import InvalidStateTransitionError
from ..core.logging import get_logger
from .schemas import ExecutionState, TaskStatus

logger = get_logger(__name__)


class StateMachine:
    """Finite state machine for task execution.
    
    Manages valid transitions between task states and validates
    that all state changes are legal.
    """
    
    # Valid state transitions as adjacency list
    VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
        TaskStatus.PENDING: [
            TaskStatus.PLANNING,
            TaskStatus.EXECUTING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        ],
        TaskStatus.PLANNING: [
            TaskStatus.EXECUTING,
            TaskStatus.WAITING_INPUT,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        ],
        TaskStatus.EXECUTING: [
            TaskStatus.EXECUTING,  # Self-transition for continuous execution
            TaskStatus.WAITING_INPUT,
            TaskStatus.REVIEWING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        ],
        TaskStatus.WAITING_INPUT: [
            TaskStatus.PLANNING,
            TaskStatus.EXECUTING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        ],
        TaskStatus.REVIEWING: [
            TaskStatus.EXECUTING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        ],
        TaskStatus.COMPLETED: [],  # Terminal state
        TaskStatus.FAILED: [],  # Terminal state
    }
    
    def __init__(self) -> None:
        """Initialize state machine."""
        pass
    
    def transition(
        self,
        state: ExecutionState,
        new_status: TaskStatus
    ) -> ExecutionState:
        """Transition to a new state.
        
        Args:
            state: Current execution state.
            new_status: Target status.
            
        Returns:
            Updated execution state.
            
        Raises:
            InvalidStateTransitionError: If transition is not valid.
        """
        current_status = state.status
        
        if not self.is_valid_transition(current_status, new_status):
            valid = self.get_valid_transitions(current_status)
            raise InvalidStateTransitionError(
                from_state=current_status.value,
                to_state=new_status.value,
                valid_transitions=[s.value for s in valid]
            )
        
        # Perform transition
        old_status = state.status
        state.status = new_status
        state.updated_at = __import__('datetime').datetime.utcnow()
        
        logger.info(
            "State transition",
            task_id=str(state.task_id),
            from_state=old_status.value,
            to_state=new_status.value,
            step=state.step_count
        )
        
        return state
    
    def is_valid_transition(
        self,
        from_status: TaskStatus,
        to_status: TaskStatus
    ) -> bool:
        """Check if a transition is valid.
        
        Args:
            from_status: Current status.
            to_status: Target status.
            
        Returns:
            True if transition is valid.
        """
        valid_targets = self.VALID_TRANSITIONS.get(from_status, [])
        return to_status in valid_targets
    
    def get_valid_transitions(self, status: TaskStatus) -> list[TaskStatus]:
        """Get list of valid transitions from a state.
        
        Args:
            status: Current status.
            
        Returns:
            List of valid target statuses.
        """
        return self.VALID_TRANSITIONS.get(status, [])
    
    def is_terminal(self, status: TaskStatus) -> bool:
        """Check if a status is terminal (no outgoing transitions).
        
        Args:
            status: Status to check.
            
        Returns:
            True if terminal.
        """
        return status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
    
    def can_execute(self, state: ExecutionState) -> bool:
        """Check if execution can proceed.
        
        Args:
            state: Current state.
            
        Returns:
            True if execution can continue.
        """
        return (
            state.status in [
                TaskStatus.PENDING,
                TaskStatus.PLANNING,
                TaskStatus.EXECUTING,
            ]
            and not state.has_exceeded_steps()
            and not state.is_complete()
        )
    
    def mark_failed(
        self,
        state: ExecutionState,
        error: str
    ) -> ExecutionState:
        """Mark execution as failed.
        
        Args:
            state: Current state.
            error: Error message.
            
        Returns:
            Updated state.
        """
        state.error = error
        return self.transition(state, TaskStatus.FAILED)
    
    def mark_completed(self, state: ExecutionState) -> ExecutionState:
        """Mark execution as completed.
        
        Args:
            state: Current state.
            
        Returns:
            Updated state.
        """
        return self.transition(state, TaskStatus.COMPLETED)


class WorkflowStateMachine(StateMachine):
    """Extended state machine for specific workflow patterns."""
    
    def __init__(self, workflow_type: str) -> None:
        """Initialize with workflow type.
        
        Args:
            workflow_type: Type of workflow (sequential, concurrent, etc.)
        """
        super().__init__()
        self.workflow_type = workflow_type
    
    def transition_with_pattern(
        self,
        state: ExecutionState,
        new_status: TaskStatus,
        pattern_data: dict[str, Any] | None = None
    ) -> ExecutionState:
        """Transition with pattern-specific validation.
        
        Args:
            state: Current state.
            new_status: Target status.
            pattern_data: Optional pattern-specific data.
            
        Returns:
            Updated state.
        """
        # Add pattern-specific logic here
        if pattern_data:
            state.metadata.update(pattern_data)
        
        return self.transition(state, new_status)


# Global state machine instance
_state_machine: StateMachine | None = None


def get_state_machine() -> StateMachine:
    """Get the global state machine instance.
    
    Returns:
        StateMachine instance.
    """
    global _state_machine
    if _state_machine is None:
        _state_machine = StateMachine()
    return _state_machine