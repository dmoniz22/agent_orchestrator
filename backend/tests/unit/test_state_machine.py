"""Unit tests for the state machine."""

import pytest
from uuid import uuid4

from src.core.exceptions import InvalidStateTransitionError
from src.orchestration.schemas import ExecutionState, TaskStatus
from src.orchestration.state_machine import StateMachine, get_state_machine


class TestStateMachine:
    """Test cases for StateMachine."""
    
    @pytest.fixture
    def state_machine(self):
        """Create a fresh state machine."""
        return StateMachine()
    
    @pytest.fixture
    def execution_state(self):
        """Create a sample execution state."""
        return ExecutionState(
            session_id=uuid4(),
            original_query="Test query",
            status=TaskStatus.PENDING
        )
    
    def test_is_valid_transition_pending_to_planning(self, state_machine):
        """Test PENDING -> PLANNING is valid."""
        assert state_machine.is_valid_transition(
            TaskStatus.PENDING,
            TaskStatus.PLANNING
        ) is True
    
    def test_is_valid_transition_pending_to_executing(self, state_machine):
        """Test PENDING -> EXECUTING is valid."""
        assert state_machine.is_valid_transition(
            TaskStatus.PENDING,
            TaskStatus.EXECUTING
        ) is True
    
    def test_is_valid_transition_pending_to_completed(self, state_machine):
        """Test PENDING -> COMPLETED is valid."""
        assert state_machine.is_valid_transition(
            TaskStatus.PENDING,
            TaskStatus.COMPLETED
        ) is True
    
    def test_is_valid_transition_pending_to_failed(self, state_machine):
        """Test PENDING -> FAILED is valid."""
        assert state_machine.is_valid_transition(
            TaskStatus.PENDING,
            TaskStatus.FAILED
        ) is True
    
    def test_is_valid_transition_executing_to_reviewing(self, state_machine):
        """Test EXECUTING -> REVIEWING is valid."""
        assert state_machine.is_valid_transition(
            TaskStatus.EXECUTING,
            TaskStatus.REVIEWING
        ) is True
    
    def test_is_valid_transition_executing_to_waiting(self, state_machine):
        """Test EXECUTING -> WAITING_INPUT is valid."""
        assert state_machine.is_valid_transition(
            TaskStatus.EXECUTING,
            TaskStatus.WAITING_INPUT
        ) is True
    
    def test_invalid_transition_completed_to_executing(self, state_machine):
        """Test COMPLETED -> EXECUTING is invalid (terminal state)."""
        assert state_machine.is_valid_transition(
            TaskStatus.COMPLETED,
            TaskStatus.EXECUTING
        ) is False
    
    def test_invalid_transition_failed_to_pending(self, state_machine):
        """Test FAILED -> PENDING is invalid (terminal state)."""
        assert state_machine.is_valid_transition(
            TaskStatus.FAILED,
            TaskStatus.PENDING
        ) is False
    
    def test_get_valid_transitions_pending(self, state_machine):
        """Test getting valid transitions from PENDING."""
        valid = state_machine.get_valid_transitions(TaskStatus.PENDING)
        assert TaskStatus.PLANNING in valid
        assert TaskStatus.EXECUTING in valid
        assert TaskStatus.COMPLETED in valid
        assert TaskStatus.FAILED in valid
        assert TaskStatus.WAITING_INPUT not in valid
    
    def test_get_valid_transitions_completed(self, state_machine):
        """Test getting valid transitions from COMPLETED (terminal)."""
        valid = state_machine.get_valid_transitions(TaskStatus.COMPLETED)
        assert valid == []
    
    def test_transition_success(self, state_machine, execution_state):
        """Test successful state transition."""
        new_state = state_machine.transition(
            execution_state,
            TaskStatus.PLANNING
        )
        assert new_state.status == TaskStatus.PLANNING
    
    def test_transition_failure_invalid(self, state_machine, execution_state):
        """Test that invalid transitions raise exception."""
        execution_state.status = TaskStatus.COMPLETED
        
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            state_machine.transition(execution_state, TaskStatus.EXECUTING)
        
        assert "completed" in str(exc_info.value.from_state)
        assert "executing" in str(exc_info.value.to_state)
    
    def test_is_terminal_completed(self, state_machine):
        """Test COMPLETED is terminal."""
        assert state_machine.is_terminal(TaskStatus.COMPLETED) is True
    
    def test_is_terminal_failed(self, state_machine):
        """Test FAILED is terminal."""
        assert state_machine.is_terminal(TaskStatus.FAILED) is True
    
    def test_is_terminal_executing(self, state_machine):
        """Test EXECUTING is not terminal."""
        assert state_machine.is_terminal(TaskStatus.EXECUTING) is False
    
    def test_can_execute_pending(self, state_machine, execution_state):
        """Test can_execute returns True for PENDING."""
        assert state_machine.can_execute(execution_state) is True
    
    def test_can_execute_completed(self, state_machine, execution_state):
        """Test can_execute returns False for COMPLETED."""
        execution_state.status = TaskStatus.COMPLETED
        assert state_machine.can_execute(execution_state) is False
    
    def test_can_execute_exceeded_steps(self, state_machine, execution_state):
        """Test can_execute returns False when steps exceeded."""
        execution_state.step_count = execution_state.max_steps
        assert state_machine.can_execute(execution_state) is False
    
    def test_mark_failed(self, state_machine, execution_state):
        """Test mark_failed sets error and transitions."""
        new_state = state_machine.mark_failed(
            execution_state,
            "Test error"
        )
        assert new_state.status == TaskStatus.FAILED
        assert new_state.error == "Test error"
    
    def test_mark_completed(self, state_machine, execution_state):
        """Test mark_completed transitions to COMPLETED."""
        execution_state.status = TaskStatus.EXECUTING
        new_state = state_machine.mark_completed(execution_state)
        assert new_state.status == TaskStatus.COMPLETED
    
    def test_get_state_machine_singleton(self):
        """Test get_state_machine returns singleton."""
        sm1 = get_state_machine()
        sm2 = get_state_machine()
        assert sm1 is sm2