"""Sequential workflow pattern implementation."""

import asyncio
from typing import Any

from src.core.logging import get_logger
from src.orchestration.schemas import ActionType, ExecutionState, StepRecord, TaskStatus
from src.orchestration.state_machine import StateMachine

logger = get_logger(__name__)


class SequentialPattern:
    """Sequential workflow pattern.
    
    Chains agent invocations, passing output of one as input to the next.
    Supports configurable agent chains with failure handling.
    """
    
    def __init__(
        self,
        state_machine: StateMachine | None = None,
        agent_registry=None
    ) -> None:
        """Initialize sequential pattern.
        
        Args:
            state_machine: State machine instance.
            agent_registry: Agent registry for lookups.
        """
        self.state_machine = state_machine or StateMachine()
        self.agent_registry = agent_registry
        logger.info("SequentialPattern initialized")
    
    async def execute(
        self,
        initial_input: str,
        agent_chain: list[str],
        state: ExecutionState | None = None,
        fail_fast: bool = True
    ) -> dict[str, Any]:
        """Execute agents sequentially.
        
        Args:
            initial_input: Initial input for first agent.
            agent_chain: List of agent IDs to execute in order.
            state: Optional execution state.
            fail_fast: Stop on first failure if True.
            
        Returns:
            Execution result with outputs from each step.
        """
        if not agent_chain:
            return {
                "success": True,
                "results": [],
                "final_output": initial_input
            }
        
        # Create state if not provided
        if state is None:
            from uuid import uuid4
            state = ExecutionState(
                session_id=uuid4(),
                original_query=initial_input
            )
        
        logger.info(
            "Starting sequential execution",
            task_id=str(state.task_id),
            agent_count=len(agent_chain)
        )
        
        results = []
        current_input = initial_input
        
        try:
            # Transition to executing
            self.state_machine.transition(state, TaskStatus.EXECUTING)
            
            for i, agent_id in enumerate(agent_chain):
                logger.info(
                    "Executing agent in sequence",
                    task_id=str(state.task_id),
                    step=i + 1,
                    agent_id=agent_id
                )
                
                try:
                    # Execute agent
                    result = await self._execute_agent(
                        agent_id,
                        current_input,
                        state,
                        step_number=i + 1
                    )
                    
                    results.append({
                        "step": i + 1,
                        "agent_id": agent_id,
                        "success": result["success"],
                        "output": result.get("output"),
                        "error": result.get("error")
                    })
                    
                    if result["success"]:
                        current_input = result.get("output", current_input)
                    else:
                        logger.warning(
                            "Agent failed in sequence",
                            task_id=str(state.task_id),
                            agent_id=agent_id,
                            error=result.get("error")
                        )
                        
                        if fail_fast:
                            self.state_machine.mark_failed(
                                state,
                                f"Agent {agent_id} failed: {result.get('error')}"
                            )
                            return {
                                "success": False,
                                "results": results,
                                "final_output": None,
                                "error": result.get("error"),
                                "failed_at_step": i + 1
                            }
                    
                except Exception as e:
                    logger.error(
                        "Exception in sequential execution",
                        task_id=str(state.task_id),
                        agent_id=agent_id,
                        error=str(e)
                    )
                    
                    results.append({
                        "step": i + 1,
                        "agent_id": agent_id,
                        "success": False,
                        "error": str(e)
                    })
                    
                    if fail_fast:
                        self.state_machine.mark_failed(state, str(e))
                        return {
                            "success": False,
                            "results": results,
                            "final_output": None,
                            "error": str(e),
                            "failed_at_step": i + 1
                        }
            
            # Mark complete
            self.state_machine.mark_completed(state)
            
            return {
                "success": True,
                "results": results,
                "final_output": current_input,
                "steps_completed": len(agent_chain)
            }
            
        except Exception as e:
            logger.error(
                "Sequential pattern failed",
                task_id=str(state.task_id),
                error=str(e)
            )
            self.state_machine.mark_failed(state, str(e))
            return {
                "success": False,
                "results": results,
                "final_output": None,
                "error": str(e)
            }
    
    async def _execute_agent(
        self,
        agent_id: str,
        input_text: str,
        state: ExecutionState,
        step_number: int
    ) -> dict[str, Any]:
        """Execute a single agent.
        
        Args:
            agent_id: Agent to execute.
            input_text: Input for agent.
            state: Execution state.
            step_number: Current step number.
            
        Returns:
            Agent execution result.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get agent from registry
            if not self.agent_registry:
                return {
                    "success": False,
                    "error": "No agent registry configured"
                }
            
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                return {
                    "success": False,
                    "error": f"Agent not found: {agent_id}"
                }
            
            # Execute agent
            output = await agent.run(input_text, state)
            
            # Record step
            duration_ms = int(
                (asyncio.get_event_loop().time() - start_time) * 1000
            )
            
            step = StepRecord(
                step_number=step_number,
                action_type=ActionType.AGENT_CALL,
                actor_id=agent_id,
                input=input_text,
                output=str(output),
                duration_ms=duration_ms,
                success=True
            )
            state.add_step(step)
            
            return {
                "success": True,
                "output": output
            }
            
        except Exception as e:
            duration_ms = int(
                (asyncio.get_event_loop().time() - start_time) * 1000
            )
            
            step = StepRecord(
                step_number=step_number,
                action_type=ActionType.AGENT_CALL,
                actor_id=agent_id,
                input=input_text,
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )
            state.add_step(step)
            
            return {
                "success": False,
                "error": str(e)
            }
