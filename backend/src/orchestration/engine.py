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
        memory_manager=None,
        agent_registry=None,
        tool_registry=None,
        max_steps: int = 10,
        default_timeout: float = 120.0,
    ) -> None:
        """Initialize orchestration engine.

        Args:
            state_machine: State machine instance.
            router: Decision router.
            collator: Result collator.
            orchestrator_agent: Orchestrator agent.
            memory_manager: Memory manager for conversation history.
            max_steps: Maximum execution steps.
            default_timeout: Default timeout per step.
        """
        self.state_machine = state_machine or get_state_machine()
        self.router = router or Router()
        self.collator = collator or Collator()
        self.orchestrator_agent = orchestrator_agent
        self.memory_manager = memory_manager
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.default_timeout = default_timeout

        logger.info(
            "OrchestrationEngine initialized",
            max_steps=max_steps,
            has_memory=memory_manager is not None,
        )

    async def run(
        self,
        query: str,
        session_id: UUID,
        available_agents: list = None,
        available_tools: list = None,
        max_steps: int | None = None,
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
        # Store user query in memory
        if self.memory_manager:
            await self.memory_manager.store_conversation_turn(
                role="user", content=query, session_id=session_id
            )

        # Load conversation history
        conversation_history = []
        if self.memory_manager:
            history_entries = await self.memory_manager.get_conversation_history(
                session_id=session_id, limit=10
            )
            from src.models.provider import Message

            for entry in history_entries:
                role = entry.metadata.get("role", "user")
                conversation_history.append(Message(role=role, content=entry.content))
            logger.info(
                "Loaded conversation history",
                session_id=str(session_id),
                history_count=len(conversation_history),
            )

        # Initialize execution state
        state = ExecutionState(
            session_id=session_id,
            original_query=query,
            current_objective=query,
            max_steps=max_steps or self.max_steps,
            available_agents=available_agents or [],
            available_tools=available_tools or [],
            conversation_history=conversation_history,
        )

        logger.info(
            "Starting orchestration",
            task_id=str(state.task_id),
            query=query[:100],
            has_memory=self.memory_manager is not None,
        )

        try:
            # Main execution loop
            last_result_text = None  # Output from previous agent/tool call
            while self.state_machine.can_execute(state):
                # Transition to planning
                if state.status == TaskStatus.PENDING:
                    self.state_machine.transition(state, TaskStatus.PLANNING)

                # Get orchestrator decision (with context from previous step)
                decision = await self._get_orchestrator_decision(state, last_result_text)

                # Execute decision (actually runs agent/tool)
                result = await self._execute_decision(decision, state)

                # Track result for next orchestrator decision
                if result.get("output"):
                    last_result_text = result["output"]

                # Check completion
                if decision.is_complete or decision.action == ActionType.FINAL_RESPONSE:
                    self.state_machine.mark_completed(state)
                    break

                # Check step limit
                if state.has_exceeded_steps():
                    logger.warning(
                        "Step limit exceeded",
                        task_id=str(state.task_id),
                        steps=state.step_count,
                    )
                    self.state_machine.mark_completed(state)
                    break

            # Collate final results
            if state.status == TaskStatus.COMPLETED:
                result = await self.collator.collate(state)

                # Store assistant response in memory
                if self.memory_manager and result.get("response"):
                    await self.memory_manager.store_conversation_turn(
                        role="assistant", content=result["response"], session_id=session_id
                    )
                    logger.info(
                        "Stored assistant response in memory",
                        session_id=str(session_id),
                        response_length=len(result["response"]),
                    )

                return result
            else:
                return self.collator.format_error(state)

        except Exception as e:
            logger.error("Orchestration failed", task_id=str(state.task_id), error=str(e))
            self.state_machine.mark_failed(state, str(e))
            return self.collator.format_error(state)

    async def _get_orchestrator_decision(
        self, state: ExecutionState, last_result_text: str | None = None
    ) -> OrchestratorDecision:
        """Get decision from orchestrator agent.

        Args:
            state: Current execution state.
            last_result_text: Output from previous agent/tool execution.

        Returns:
            Orchestrator decision.
        """
        # Transition to executing
        self.state_machine.transition(state, TaskStatus.EXECUTING)

        if not self.orchestrator_agent:
            return OrchestratorDecision(
                reasoning="No orchestrator agent configured - echoing input",
                action=ActionType.FINAL_RESPONSE,
                input=state.original_query,
                is_complete=True,
            )

        try:
            # If we have a result from a previous step, pass it to the orchestrator
            # so it knows the agent/tool has completed and can decide next steps
            if last_result_text:
                input_text = (
                    f"Original query: {state.original_query}\n\n"
                    f"Previous agent/tool output:\n{last_result_text}\n\n"
                    f"Based on the output above, decide what to do next. "
                    f"If the task is complete, use final_response with the answer. "
                    f"If more work is needed, route to another agent or tool."
                )
            else:
                input_text = state.original_query

            # Call orchestrator agent with conversation history
            decision = await self.orchestrator_agent.run(
                input_text=input_text,
                context={
                    "available_agents": state.available_agents,
                    "available_tools": state.available_tools,
                    "conversation_history": state.conversation_history,
                },
            )

            logger.info(
                "Orchestrator returned decision",
                decision_type=type(decision).__name__,
                decision_preview=str(decision)[:200] if decision else "None",
            )

            # If decision is a dict, use it directly
            if isinstance(decision, dict):
                orch_decision = OrchestratorDecision(**decision)
                logger.info(
                    "Created OrchestratorDecision",
                    action=orch_decision.action,
                    input_field=orch_decision.input[:100] if orch_decision.input else "None",
                )
                return orch_decision

            # If decision is a string, treat it as final response
            return OrchestratorDecision(
                reasoning="Orchestrator response",
                action=ActionType.FINAL_RESPONSE,
                input=str(decision),
                is_complete=True,
            )

        except Exception as e:
            logger.error("Orchestrator decision failed", error=str(e))
            return OrchestratorDecision(
                reasoning=f"Orchestrator failed: {str(e)}",
                action=ActionType.FINAL_RESPONSE,
                input="I apologize, but I encountered an error while processing your request. Both the local AI (Ollama) and the cloud fallback (OpenRouter) are unavailable. Please check that Ollama is running locally, or that your OpenRouter API key is valid.",
                is_complete=True,
            )

    async def _execute_decision(
        self, decision: OrchestratorDecision, state: ExecutionState
    ) -> dict[str, Any]:
        """Execute an orchestrator decision.

        Args:
            decision: Orchestrator decision.
            state: Current state.

        Returns:
            Execution result with 'output' field containing agent/tool response.
        """
        start_time = asyncio.get_event_loop().time()

        # Handle final response directly without routing
        if decision.action == ActionType.FINAL_RESPONSE:
            logger.info(
                "Executing FINAL_RESPONSE",
                decision_input=decision.input[:100] if decision.input else "None",
                original_query=state.original_query[:100],
            )

            step = StepRecord(
                step_number=state.step_count + 1,
                action_type=decision.action,
                actor_id="orchestrator",
                input=decision.input,
                output=decision.input,
                duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                success=True,
            )
            state.add_step(step)
            state.add_partial_result(decision.input)

            return {"action": "final_response", "output": decision.input, "success": True}

        try:
            # Validate decision via router (checks agent/tool exists)
            dispatch_info = await self.router.dispatch(decision, state)

            if not dispatch_info.get("success"):
                # Router returned an error (agent/tool not found)
                error_output = dispatch_info.get("output", "Unknown dispatch error")
                step = StepRecord(
                    step_number=state.step_count + 1,
                    action_type=decision.action,
                    actor_id=decision.agent_id or decision.tool_id or "unknown",
                    input=decision.input,
                    output=error_output,
                    duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                    success=False,
                    error=dispatch_info.get("error"),
                )
                state.add_step(step)
                state.add_partial_result(error_output)
                return {"action": decision.action.value, "output": error_output, "success": False}

            # Actually execute the agent or tool
            actual_output = ""

            if decision.action == ActionType.AGENT_CALL:
                agent_id = decision.agent_id
                agent = self.agent_registry.get_agent(agent_id) if self.agent_registry else None
                if agent:
                    logger.info(
                        "Executing agent", agent_id=agent_id, input_preview=decision.input[:100]
                    )
                    agent_result = await agent.run(
                        input_text=decision.input,
                        context={"conversation_history": state.conversation_history},
                    )
                    # agent_result could be a string or dict
                    actual_output = (
                        agent_result if isinstance(agent_result, str) else str(agent_result)
                    )
                    logger.info(
                        "Agent execution complete",
                        agent_id=agent_id,
                        output_length=len(actual_output),
                    )
                else:
                    actual_output = f"Agent '{agent_id}' not found in registry"

            elif decision.action == ActionType.TOOL_CALL:
                tool_id = decision.tool_id
                tool = self.tool_registry.get_tool(tool_id) if self.tool_registry else None
                if tool:
                    params = decision.tool_parameters or {}
                    logger.info("Executing tool", tool_id=tool_id, params=params)
                    tool_result = await tool.run(**params)
                    actual_output = (
                        str(tool_result.result)
                        if tool_result.success
                        else f"Tool error: {tool_result.error}"
                    )
                    logger.info(
                        "Tool execution complete", tool_id=tool_id, success=tool_result.success
                    )
                else:
                    actual_output = f"Tool '{tool_id}' not found in registry"

            # Record step
            step = StepRecord(
                step_number=state.step_count + 1,
                action_type=decision.action,
                actor_id=decision.agent_id or decision.tool_id or "orchestrator",
                input=decision.input,
                output=actual_output,
                duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                success=True,
            )
            state.add_step(step)
            state.add_partial_result(actual_output)

            return {"action": decision.action.value, "output": actual_output, "success": True}

        except Exception as e:
            logger.error("Decision execution failed", error=str(e))

            step = StepRecord(
                step_number=state.step_count + 1,
                action_type=decision.action,
                actor_id=decision.agent_id or decision.tool_id or "orchestrator",
                input=decision.input,
                duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                success=False,
                error=str(e),
            )
            state.add_step(step)

            raise OrchestrationError(
                message=f"Failed to execute decision: {str(e)}",
                details={"decision": decision.model_dump()},
            )


# Global engine instance
_engine: OrchestrationEngine | None = None


async def get_orchestration_engine(
    state_machine: StateMachine | None = None,
    router: Router | None = None,
    collator: Collator | None = None,
    orchestrator_agent=None,
    memory_manager=None,
    agent_registry=None,
    tool_registry=None,
    max_steps: int = 10,
) -> OrchestrationEngine:
    """Get or create global orchestration engine.

    Args:
        state_machine: State machine instance.
        router: Decision router.
        collator: Result collator.
        orchestrator_agent: Orchestrator agent.
        memory_manager: Memory manager for conversation history.
        agent_registry: Agent registry for executing agent calls.
        tool_registry: Tool registry for executing tool calls.
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
            memory_manager=memory_manager,
            agent_registry=agent_registry,
            tool_registry=tool_registry,
            max_steps=max_steps,
        )
    return _engine
