"""Result collator for synthesizing execution results."""

import json
import re
from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from .schemas import ExecutionState, StepRecord

logger = get_logger(__name__)


class Collator:
    """Collates and synthesizes execution results.

    Takes partial results from execution history and synthesizes
    them into a coherent final response.
    """

    def __init__(self, model_provider=None) -> None:
        """Initialize collator.

        Args:
            model_provider: Optional model provider for synthesis.
        """
        self.model_provider = model_provider
        logger.info("Collator initialized")

    async def collate(self, state: ExecutionState) -> dict[str, Any]:
        """Collate results from execution state.

        Args:
            state: Execution state with history.

        Returns:
            Collated result with response and trace.
        """
        logger.info("Collating results", task_id=str(state.task_id), steps=state.step_count)

        # Build execution trace
        trace = self._build_trace(state)

        # Synthesize final response
        if state.partial_results:
            response = self._synthesize_response(state)
        else:
            response = state.original_query

        return {
            "task_id": str(state.task_id),
            "status": state.status.value,
            "response": response,
            "trace": trace,
            "steps_taken": state.step_count,
            "agents_invoked": trace["agents"],
            "tools_used": trace["tools"],
        }

    def _build_trace(self, state: ExecutionState) -> dict[str, Any]:
        """Build execution trace from history.

        Args:
            state: Execution state.

        Returns:
            Execution trace summary.
        """
        agents = []
        tools = []
        steps = []

        for step in state.history:
            step_info = {
                "step_number": step.step_number,
                "action": step.action_type.value,
                "actor": step.actor_id,
                "success": step.success,
                "duration_ms": step.duration_ms,
            }

            if step.error:
                step_info["error"] = step.error

            steps.append(step_info)

            if step.action_type.value == "call_agent":
                if step.actor_id not in agents:
                    agents.append(step.actor_id)
            elif step.action_type.value == "use_tool":
                if step.actor_id not in tools:
                    tools.append(step.actor_id)

        return {"agents": agents, "tools": tools, "steps": steps, "total_steps": len(steps)}

    def _try_extract_output(self, result: str) -> str | None:
        """Try to extract the 'output' field from a dict-like string.

        Args:
            result: Result string that may contain a dict.

        Returns:
            Extracted output or None.
        """
        # Try JSON parse first
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "output" in parsed:
                return str(parsed["output"])
        except (json.JSONDecodeError, TypeError):
            pass

        # Try Python dict repr pattern
        match = re.search(r"['\"]output['\"]:\s*['\"](.+?)['\"](?:,|}|$)", result)
        if match:
            return match.group(1)

        return None

    def _synthesize_response(self, state: ExecutionState) -> str:
        """Synthesize response from partial results.

        Args:
            state: Execution state with partial results.

        Returns:
            Synthesized response.
        """
        if not state.partial_results:
            return state.original_query

        # If only one result, return it directly (extract output if possible)
        if len(state.partial_results) == 1:
            result = state.partial_results[0]
            extracted = self._try_extract_output(result)
            return extracted if extracted else result

        # Multiple results - find the most relevant one
        # Priority: agent/tool outputs > final responses > errors
        agent_tool_outputs = []
        final_responses = []
        error_outputs = []

        for i, result in enumerate(state.partial_results):
            extracted = self._try_extract_output(result)
            display = extracted or result

            # Classify by content patterns
            if "'success': False" in result or '"success": False' in result:
                error_outputs.append(display)
            elif "final_response" in result and i == len(state.partial_results) - 1:
                final_responses.append(display)
            else:
                agent_tool_outputs.append(display)

        # Prefer agent/tool outputs (the actual work done)
        if agent_tool_outputs:
            return agent_tool_outputs[-1]

        # Fall back to final responses
        if final_responses:
            return final_responses[-1]

        # Fall back to error messages
        if error_outputs:
            return error_outputs[-1]

        # Last resort: return last result
        last = state.partial_results[-1]
        extracted = self._try_extract_output(last)
        return extracted if extracted else last

    def format_error(self, state: ExecutionState) -> dict[str, Any]:
        """Format error response.

        Args:
            state: Failed execution state.

        Returns:
            Error response.
        """
        trace = self._build_trace(state)

        return {
            "task_id": str(state.task_id),
            "status": "failed",
            "error": state.error or "Unknown error",
            "trace": trace,
            "steps_taken": state.step_count,
        }
