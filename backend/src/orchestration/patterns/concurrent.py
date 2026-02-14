"""Concurrent workflow pattern implementation."""

import asyncio
from typing import Any

from src.core.logging import get_logger
from src.orchestration.schemas import ActionType, ExecutionState, StepRecord, TaskStatus
from src.orchestration.state_machine import StateMachine

logger = get_logger(__name__)


class ConcurrentPattern:
    """Concurrent workflow pattern.
    
    Runs multiple agents in parallel using asyncio.gather()
    and aggregates results. Handles partial failures.
    """
    
    def __init__(
        self,
        state_machine: StateMachine | None = None,
        agent_registry=None
    ) -> None:
        """Initialize concurrent pattern.
        
        Args:
            state_machine: State machine instance.
            agent_registry: Agent registry for lookups.
        """
        self.state_machine = state_machine or StateMachine()
        self.agent_registry = agent_registry
        logger.info("ConcurrentPattern initialized")
    
    async def execute(
        self,
        input_text: str,
        agent_ids: list[str],
        state: ExecutionState | None = None,
        require_all_success: bool = False,
        timeout_seconds: float = 120.0
    ) -> dict[str, Any]:
        """Execute agents concurrently.
        
        Args:
            input_text: Input for all agents.
            agent_ids: List of agent IDs to execute.
            state: Optional execution state.
            require_all_success: Fail if any agent fails.
            timeout_seconds: Timeout per agent.
            
        Returns:
            Execution result with all outputs.
        """
        if not agent_ids:
            return {
                "success": True,
                "results": [],
                "successful_count": 0,
                "failed_count": 0
            }
        
        # Create state if not provided
        if state is None:
            from uuid import uuid4
            state = ExecutionState(
                session_id=uuid4(),
                original_query=input_text
            )
        
        logger.info(
            "Starting concurrent execution",
            task_id=str(state.task_id),
            agent_count=len(agent_ids)
        )
        
        try:
            # Transition to executing
            self.state_machine.transition(state, TaskStatus.EXECUTING)
            
            # Create tasks for all agents
            tasks = [
                self._execute_agent_with_timeout(
                    agent_id,
                    input_text,
                    state,
                    timeout_seconds
                )
                for agent_id in agent_ids
            ]
            
            # Execute all concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            processed_results = []
            successful = 0
            failed = 0
            
            for i, (agent_id, result) in enumerate(zip(agent_ids, results)):
                if isinstance(result, Exception):
                    processed_results.append({
                        "agent_id": agent_id,
                        "success": False,
                        "output": None,
                        "error": str(result)
                    })
                    failed += 1
                else:
                    processed_results.append(result)
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
            
            # Determine overall success
            all_successful = successful == len(agent_ids)
            any_successful = successful > 0
            
            if require_all_success and not all_successful:
                self.state_machine.mark_failed(
                    state,
                    f"Only {successful}/{len(agent_ids)} agents succeeded"
                )
                return {
                    "success": False,
                    "results": processed_results,
                    "successful_count": successful,
                    "failed_count": failed,
                    "error": "Not all agents succeeded"
                }
            
            if not any_successful:
                self.state_machine.mark_failed(
                    state,
                    "All agents failed"
                )
                return {
                    "success": False,
                    "results": processed_results,
                    "successful_count": 0,
                    "failed_count": failed,
                    "error": "All agents failed"
                }
            
            # Mark complete
            self.state_machine.mark_completed(state)
            
            return {
                "success": True,
                "results": processed_results,
                "successful_count": successful,
                "failed_count": failed,
                "all_succeeded": all_successful
            }
            
        except Exception as e:
            logger.error(
                "Concurrent pattern failed",
                task_id=str(state.task_id),
                error=str(e)
            )
            self.state_machine.mark_failed(state, str(e))
            return {
                "success": False,
                "results": [],
                "error": str(e)
            }
    
    async def _execute_agent_with_timeout(
        self,
        agent_id: str,
        input_text: str,
        state: ExecutionState,
        timeout_seconds: float
    ) -> dict[str, Any]:
        """Execute agent with timeout.
        
        Args:
            agent_id: Agent to execute.
            input_text: Input for agent.
            state: Execution state.
            timeout_seconds: Timeout.
            
        Returns:
            Execution result.
        """
        try:
            return await asyncio.wait_for(
                self._execute_agent(agent_id, input_text, state),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            return {
                "agent_id": agent_id,
                "success": False,
                "output": None,
                "error": f"Timeout after {timeout_seconds}s"
            }
    
    async def _execute_agent(
        self,
        agent_id: str,
        input_text: str,
        state: ExecutionState
    ) -> dict[str, Any]:
        """Execute a single agent.
        
        Args:
            agent_id: Agent to execute.
            input_text: Input for agent.
            state: Execution state.
            
        Returns:
            Agent execution result.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get agent from registry
            if not self.agent_registry:
                return {
                    "agent_id": agent_id,
                    "success": False,
                    "output": None,
                    "error": "No agent registry configured"
                }
            
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                return {
                    "agent_id": agent_id,
                    "success": False,
                    "output": None,
                    "error": f"Agent not found: {agent_id}"
                }
            
            # Execute agent
            output = await agent.run(input_text, state)
            
            # Record step
            duration_ms = int(
                (asyncio.get_event_loop().time() - start_time) * 1000
            )
            
            step = StepRecord(
                step_number=state.step_count + 1,
                action_type=ActionType.AGENT_CALL,
                actor_id=agent_id,
                input=input_text,
                output=str(output),
                duration_ms=duration_ms,
                success=True
            )
            state.add_step(step)
            
            return {
                "agent_id": agent_id,
                "success": True,
                "output": output,
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            duration_ms = int(
                (asyncio.get_event_loop().time() - start_time) * 1000
            )
            
            step = StepRecord(
                step_number=state.step_count + 1,
                action_type=ActionType.AGENT_CALL,
                actor_id=agent_id,
                input=input_text,
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )
            state.add_step(step)
            
            return {
                "agent_id": agent_id,
                "success": False,
                "output": None,
                "error": str(e),
                "duration_ms": duration_ms
            }
