"""Result collator for synthesizing execution results."""

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
    
    async def collate(
        self,
        state: ExecutionState
    ) -> dict[str, Any]:
        """Collate results from execution state.
        
        Args:
            state: Execution state with history.
            
        Returns:
            Collated result with response and trace.
        """
        logger.info(
            "Collating results",
            task_id=str(state.task_id),
            steps=state.step_count
        )
        
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
            "tools_used": trace["tools"]
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
                "duration_ms": step.duration_ms
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
        
        return {
            "agents": agents,
            "tools": tools,
            "steps": steps,
            "total_steps": len(steps)
        }
    
    def _synthesize_response(self, state: ExecutionState) -> str:
        """Synthesize response from partial results.
        
        Args:
            state: Execution state with partial results.
            
        Returns:
            Synthesized response.
        """
        if not state.partial_results:
            return state.original_query
        
        # If only one result, return it directly
        if len(state.partial_results) == 1:
            result = state.partial_results[0]
            # Try to extract just the conversational output from JSON-like results
            if "'output':" in result or '"output":' in result:
                import re
                # Look for output field in dict-like string
                match = re.search(r"['\"]output['\"]:\s*['\"](.+?)['\"](?:,|})", result)
                if match:
                    return match.group(1)
            return result
        
        # Multiple results - filter to find the most relevant one
        # Priority: final_response > successful tool/agent calls > errors
        final_responses = []
        error_responses = []
        other_responses = []
        
        for result in state.partial_results:
            if "final_response" in result or "action': 'final_response" in result:
                final_responses.append(result)
            elif "'success': False" in result or '"success": False' in result:
                # Extract just the output field from error responses
                import re
                match = re.search(r"['\"]output['\"]:\s*['\"](.+?)['\"](?:,|})", result)
                if match:
                    error_responses.append(match.group(1))
                else:
                    error_responses.append(result)
            else:
                other_responses.append(result)
        
        # Return the last final response if available
        if final_responses:
            last = final_responses[-1]
            import re
            match = re.search(r"['\"]output['\"]:\s*['\"](.+?)['\"](?:,|})", last)
            if match:
                return match.group(1)
            return last
        
        # Return the last error response with helpful message
        if error_responses:
            return error_responses[-1]
        
        # Fallback to last result
        return state.partial_results[-1]
    
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
            "steps_taken": state.step_count
        }
