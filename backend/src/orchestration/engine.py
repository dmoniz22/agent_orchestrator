"""Orchestration engine for managing task execution."""

import asyncio
from typing import Any
from uuid import UUID

from src.core.exceptions import OrchestrationError
from src.core.logging import get_logger
from .collator import Collator
from .router import Router
from .schemas import (
    ActionType,
    ExecutionState,
    OrchestratorDecision,
    StepRecord,
    TaskStatus,
)
from .state_machine import StateMachine, get_state_machine

logger = get_logger(__name__)


class OrchestrationEngine:
    """Main orchestration engine.
    
    Coordinates the execution flow from initial query through
    orchestrator decisions to final response.
    """
    
    def __init__(
        self,
        state_machine: StateMachine | None = None,
        router: Router | None = None,
        collator: Collator | None = None,
        orchestrator_agent=None,
        max_steps: int = 10,
        default_timeout: float = 120.0
    ) -> None:
        """Initialize orchestration engine.
        
        Args:
            state_machine: State machine instance.
            router: Decision router.
            collator: Result collator.
            orchestrator_agent: Orchestrator agent.
            max_steps: Maximum execution steps.
            default_timeout: Default timeout per step.
        """
        self.state_machine = state_machine or get_state_machine()
        self.router = router or Router()
        self.collator = collator or Collator()
        self.orchestrator_agent = orchestrator_agent
        self.max_steps = max_steps
        self.default_timeout = default_timeout
        
        logger.info(
            "OrchestrationEngine initialized",
            max_steps=max_steps
        )
    
    async def run(
        self,
        query: str,
        session_id: UUID,
        available_agents: list = None,
        available_tools: list = None,
        max_steps: int | None = None
    ) -> dict[str, Any]:
        """Execute a task from query to completion.
        
        Args:
            query: User query.
            session_id: Session identifier.
            available_agents: List of available agents.
            available_tools: List of available tools.
            max_steps: Override max steps.
            
        Returns:
            Execution result.
        """
        # Initialize execution state
        state = ExecutionState(
            session_id=session_id,
            original_query=query,
            current_objective=query,
            max_steps=max_steps or self.max_steps,
            available_agents=available_agents or [],
            available_tools=available_tools or []
        )
        
        logger.info(
            "Starting orchestration",
            task_id=str(state.task_id),
            query=query[:100]
        )
        
        try:
            # Main execution loop
            while self.state_machine.can_execute(state):
                # Transition to planning
                if state.status == TaskStatus.PENDING:
                    self.state_machine.transition(state, TaskStatus.PLANNING)
                
                # Get orchestrator decision
                decision = await self._get_orchestrator_decision(state)
                
                # Execute decision
                result = await self._execute_decision(decision, state)
                
                # Check completion
                if decision.is_complete or decision.action == ActionType.FINAL_RESPONSE:
                    self.state_machine.mark_completed(state)
                    break
                
                # Check step limit
                if state.has_exceeded_steps():
                    logger.warning(
                        "Step limit exceeded",
                        task_id=str(state.task_id),
                        steps=state.step_count
                    )
                    self.state_machine.mark_completed(state)
                    break
            
            # Collate final results
            if state.status == TaskStatus.COMPLETED:
                return await self.collator.collate(state)
            else:
                return self.collator.format_error(state)
                
        except Exception as e:
            logger.error(
                "Orchestration failed",
                task_id=str(state.task_id),
                error=str(e)
            )
            self.state_machine.mark_failed(state, str(e))
            return self.collator.format_error(state)
    
    async def _get_orchestrator_decision(
        self,
        state: ExecutionState
    ) -> OrchestratorDecision:
        """Get decision from orchestrator agent.
        
        Args:
            state: Current execution state.
            
        Returns:
            Orchestrator decision.
        """
        # Transition to executing
        self.state_machine.transition(state, TaskStatus.EXECUTING)
        
        if not self.orchestrator_agent:
            # Default: complete with input as response
            return OrchestratorDecision(
                reasoning="No orchestrator agent configured - echoing input",
                action=ActionType.FINAL_RESPONSE,
                input=state.original_query,
                is_complete=True
            )
        
        try:
            # Call orchestrator agent
            decision = await self.orchestrator_agent.run(
                input_text=state.original_query,
                context={
                    "available_agents": state.available_agents,
                    "available_tools": state.available_tools
                }
            )
            
            # If decision is a dict, use it directly
            if isinstance(decision, dict):
                return OrchestratorDecision(**decision)
            
            # If decision is a string, treat it as final response
            return OrchestratorDecision(
                reasoning="Orchestrator response",
                action=ActionType.FINAL_RESPONSE,
                input=str(decision),
                is_complete=True
            )
            
        except Exception as e:
            logger.error(
                "Orchestrator decision failed",
                error=str(e)
            )
            # Fallback: complete with error
            return OrchestratorDecision(
                reasoning=f"Orchestrator failed: {str(e)}",
                action=ActionType.FINAL_RESPONSE,
                input=state.original_query,
                is_complete=True
            )
    
    async def _execute_decision(
        self,
        decision: OrchestratorDecision,
        state: ExecutionState
    ) -> dict[str, Any]:
        """Execute an orchestrator decision.
        
        Args:
            decision: Orchestrator decision.
            state: Current state.
            
        Returns:
            Execution result.
        """
        start_time = asyncio.get_event_loop().time()
        
        # Handle final response directly without routing
        if decision.action == ActionType.FINAL_RESPONSE:
            step = StepRecord(
                step_number=state.step_count + 1,
                action_type=decision.action,
                actor_id="orchestrator",
                input=decision.input,
                output=decision.input,
                duration_ms=int(
                    (asyncio.get_event_loop().time() - start_time) * 1000
                ),
                success=True
            )
            state.add_step(step)
            state.add_partial_result(decision.input)
            
            return {
                "action": "final_response",
                "output": decision.input,
                "success": True
            }
        
        try:
            # Route decision for agent/tool calls
            result = await self.router.dispatch(decision, state)
            
            # Record step
            step = StepRecord(
                step_number=state.step_count + 1,
                action_type=decision.action,
                actor_id=decision.agent_id or decision.tool_id or "orchestrator",
                input=decision.input,
                output=str(result),
                duration_ms=int(
                    (asyncio.get_event_loop().time() - start_time) * 1000
                ),
                success=result.get("success", True)
            )
            state.add_step(step)
            
            # Add partial result
            if result.get("success"):
                state.add_partial_result(str(result))
            
            return result
            
        except Exception as e:
            logger.error(
                "Decision execution failed",
                error=str(e)
            )
            
            # Record failed step
            step = StepRecord(
                step_number=state.step_count + 1,
                action_type=decision.action,
                actor_id=decision.agent_id or decision.tool_id or "orchestrator",
                input=decision.input,
                duration_ms=int(
                    (asyncio.get_event_loop().time() - start_time) * 1000
                ),
                success=False,
                error=str(e)
            )
            state.add_step(step)
            
            raise OrchestrationError(
                message=f"Failed to execute decision: {str(e)}",
                details={"decision": decision.model_dump()}
            )


# Global engine instance
_engine: OrchestrationEngine | None = None


async def get_orchestration_engine(
    state_machine: StateMachine | None = None,
    router: Router | None = None,
    collator: Collator | None = None,
    orchestrator_agent=None,
    max_steps: int = 10
) -> OrchestrationEngine:
    """Get or create global orchestration engine.
    
    Args:
        state_machine: State machine instance.
        router: Decision router.
        collator: Result collator.
        orchestrator_agent: Orchestrator agent.
        max_steps: Maximum steps.
        
    Returns:
        OrchestrationEngine instance.
    """
    global _engine
    if _engine is None:
        _engine = OrchestrationEngine(
            state_machine=state_machine,
            router=router,
            collator=collator,
            orchestrator_agent=orchestrator_agent,
            max_steps=max_steps
        )
    return _engine
