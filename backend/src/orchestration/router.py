"""Decision router for dispatching orchestrator decisions."""

from typing import Any
from uuid import UUID

from src.core.exceptions import RouterError
from src.core.logging import get_logger
from .schemas import ActionType, ExecutionState, OrchestratorDecision

logger = get_logger(__name__)


class Router:
    """Routes orchestrator decisions to agents and tools.
    
    Validates decisions and dispatches to the appropriate
    handler (agent or tool).
    """
    
    def __init__(
        self,
        agent_registry=None,
        tool_registry=None
    ) -> None:
        """Initialize router.
        
        Args:
            agent_registry: Agent registry for lookups.
            tool_registry: Tool registry for lookups.
        """
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry
        logger.info("Router initialized")
    
    async def dispatch(
        self,
        decision: OrchestratorDecision,
        state: ExecutionState
    ) -> dict[str, Any]:
        """Dispatch a decision to the appropriate handler.
        
        Args:
            decision: Orchestrator decision.
            state: Current execution state.
            
        Returns:
            Execution result.
            
        Raises:
            RouterError: If dispatch fails.
        """
        action = decision.action
        
        logger.info(
            "Dispatching decision",
            action=action.value,
            task_id=str(state.task_id)
        )
        
        if action == ActionType.AGENT_CALL:
            return await self._dispatch_agent(decision, state)
        elif action == ActionType.TOOL_CALL:
            return await self._dispatch_tool(decision, state)
        elif action == ActionType.FINAL_RESPONSE:
            return await self._dispatch_final(decision, state)
        else:
            raise RouterError(
                message=f"Unknown action type: {action}",
                action=action.value
            )
    
    async def _dispatch_agent(
        self,
        decision: OrchestratorDecision,
        state: ExecutionState
    ) -> dict[str, Any]:
        """Dispatch to an agent.
        
        Args:
            decision: Decision with agent_id.
            state: Execution state.
            
        Returns:
            Agent execution result.
        """
        agent_id = decision.agent_id
        
        if not agent_id:
            raise RouterError(
                message="agent_id required for AGENT_CALL action",
                action="agent_call"
            )
        
        # Validate agent exists
        if self.agent_registry:
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                raise RouterError(
                    message=f"Agent not found: {agent_id}",
                    agent_id=agent_id
                )
        
        logger.info(
            "Dispatching to agent",
            agent_id=agent_id,
            task_id=str(state.task_id)
        )
        
        # Return dispatch info (actual execution happens in engine)
        return {
            "action": "agent_call",
            "agent_id": agent_id,
            "input": decision.input,
            "success": True
        }
    
    async def _dispatch_tool(
        self,
        decision: OrchestratorDecision,
        state: ExecutionState
    ) -> dict[str, Any]:
        """Dispatch to a tool.
        
        Args:
            decision: Decision with tool_id.
            state: Execution state.
            
        Returns:
            Tool execution result.
        """
        tool_id = decision.tool_id
        
        if not tool_id:
            raise RouterError(
                message="tool_id required for TOOL_CALL action",
                action="tool_call"
            )
        
        # Validate tool exists
        if self.tool_registry:
            tool = self.tool_registry.get_tool(tool_id)
            if not tool:
                raise RouterError(
                    message=f"Tool not found: {tool_id}",
                    tool_id=tool_id
                )
        
        logger.info(
            "Dispatching to tool",
            tool_id=tool_id,
            task_id=str(state.task_id)
        )
        
        # Return dispatch info (actual execution happens in engine)
        return {
            "action": "tool_call",
            "tool_id": tool_id,
            "parameters": decision.tool_parameters or {},
            "input": decision.input,
            "success": True
        }
    
    async def _dispatch_final(
        self,
        decision: OrchestratorDecision,
        state: ExecutionState
    ) -> dict[str, Any]:
        """Handle final response.
        
        Args:
            decision: Final decision.
            state: Execution state.
            
        Returns:
            Final response info.
        """
        logger.info(
            "Final response decision",
            task_id=str(state.task_id)
        )
        
        return {
            "action": "final_response",
            "input": decision.input,
            "is_complete": decision.is_complete,
            "success": True
        }
