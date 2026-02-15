"""Orchestrator agent for routing decisions."""

import json
from typing import Any

from src.agents.base import AgentConfig, BaseAgent
from src.core.logging import get_logger
from src.models.provider import Message

logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """Orchestrator agent that routes queries to specialists.
    
    Analyzes user queries and decides which agent or tool to invoke,
    returning a structured decision for the orchestration engine.
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are the OMNI orchestration agent. Your job is to analyze the user's query and either answer directly, or decide which specialist agent(s) to invoke.

For simple greetings, questions you can answer directly, or conversational responses, use "final_response" and put your answer in the "input" field.

For complex tasks requiring specialized agents or tools, output structured JSON with the following fields:
- reasoning: Your chain-of-thought analysis
- action: One of "call_agent", "use_tool", or "final_response"
- agent_id: The agent ID if action is "call_agent" (e.g., "coder", "researcher", "writer")
- tool_id: The tool ID if action is "use_tool" (e.g., "calculator.compute", "search.web")
- tool_parameters: Parameters for the tool if action is "use_tool"
- input: For "final_response", this is YOUR ANSWER to the user. For "call_agent" or "use_tool", this is what to send to that agent/tool.
- is_complete: Boolean indicating if this is the final answer

Available agents:
- researcher: For web research and information synthesis
- coder: For code generation, analysis, and GitHub operations
- writer: For long-form content, blog posts, and documentation
- social: For social media content and posting

Available tools:
- search.web: Search the web via DuckDuckGo
- file.read: Read local files
- file.write: Write to local files
- calculator.compute: Evaluate mathematical expressions

Guidelines:
1. Answer simple questions directly with "final_response"
2. Use agents for complex tasks requiring reasoning or creativity
3. Use tools for simple data retrieval or computation
4. When using final_response, write a helpful, conversational answer in the "input" field
5. Set is_complete=true when you have the final answer"""
    
    async def run(
        self,
        input_text: str,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Analyze query and return routing decision.
        
        Args:
            input_text: User query to analyze.
            context: Optional context with available agents/tools.
            
        Returns:
            Structured decision dict with action, target, input.
        """
        logger.info(
            "Orchestrator analyzing query",
            agent_id=self.agent_id,
            query=input_text[:100]
        )
        
        # Build prompt with context
        system_prompt = self._build_system_prompt(context)
        
        # Get decision from model
        messages = self.build_messages(system_prompt, input_text)
        
        response = await self.generate(
            messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        # Parse decision
        decision = self._parse_decision(response.content)
        
        logger.info(
            "Orchestrator decision",
            agent_id=self.agent_id,
            action=decision.get("action"),
            target=decision.get("agent_id") or decision.get("tool_id"),
            is_complete=decision.get("is_complete")
        )
        
        return decision
    
    def _build_system_prompt(self, context: dict[str, Any] | None) -> str:
        """Build system prompt with available resources.
        
        Args:
            context: Optional context with agents/tools.
            
        Returns:
            Complete system prompt.
        """
        base_prompt = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        if not context:
            return base_prompt
        
        # Add available agents to prompt
        lines = [base_prompt]
        
        if "available_agents" in context:
            lines.append("\nCurrently available specialist agents:")
            for agent in context["available_agents"]:
                lines.append(f"- {agent['agent_id']}: {agent.get('description', 'No description')}")
        
        if "available_tools" in context:
            lines.append("\nCurrently available tools:")
            for tool in context["available_tools"]:
                lines.append(f"- {tool['tool_id']}: {tool.get('description', 'No description')}")
        
        return "\n".join(lines)
    
    def _parse_decision(self, content: str) -> dict[str, Any]:
        """Parse decision from model response.
        
        Args:
            content: Model response content.
            
        Returns:
            Parsed decision dict.
        """
        # Try to extract JSON from content
        # Model may wrap JSON in markdown code blocks
        content = content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            decision = json.loads(content)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to infer decision from text
            logger.warning(
                "Failed to parse orchestrator response as JSON",
                content=content[:200]
            )
            decision = self._infer_decision(content)
        
        # Ensure required fields
        return {
            "reasoning": decision.get("reasoning", "No reasoning provided"),
            "action": decision.get("action", "final_response"),
            "agent_id": decision.get("agent_id"),
            "tool_id": decision.get("tool_id"),
            "tool_parameters": decision.get("tool_parameters", {}),
            "input": decision.get("input", content),
            "is_complete": decision.get("is_complete", True)
        }
    
    def _infer_decision(self, content: str) -> dict[str, Any]:
        """Infer decision from unstructured text.
        
        Args:
            content: Unstructured text response.
            
        Returns:
            Decision dict inferred from content.
        """
        # Default: treat as final response
        return {
            "reasoning": "Failed to parse structured decision",
            "action": "final_response",
            "input": content,
            "is_complete": True
        }