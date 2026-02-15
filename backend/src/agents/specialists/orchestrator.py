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
    
    DEFAULT_SYSTEM_PROMPT = """You are the OMNI multi-agent system orchestrator. Your role is to either answer the user's question directly OR route it to a specialist agent.

IMPORTANT: For most queries, especially greetings, simple questions, or conversational responses, you should ANSWER DIRECTLY using final_response.

When to answer directly (use final_response):
- Greetings ("Hello", "Hi", "How are you?")
- Simple questions you can answer from your knowledge
- Conversational responses
- General chit-chat
- Questions about yourself or the system

When to route to agents:
- Complex coding tasks → "coder" agent
- Research or current info → "researcher" agent
- Writing long content → "writer" agent
- Social media posts → "social" agent

OUTPUT FORMAT - You must output valid JSON:
{
  "reasoning": "Brief explanation of your decision",
  "action": "final_response" | "call_agent" | "use_tool",
  "agent_id": "agent_name" (only if action is "call_agent"),
  "tool_id": "tool_name" (only if action is "use_tool"),
  "input": "YOUR RESPONSE TO USER (for final_response) OR input for agent/tool",
  "is_complete": true
}

CRITICAL: For final_response, the "input" field must contain your actual conversational answer to the user, not the question they asked.

Examples:
User: "Hello!"
Output: {"action": "final_response", "input": "Hello! How can I help you today?", "is_complete": true}

User: "What is 2+2?"
Output: {"action": "final_response", "input": "2+2 equals 4.", "is_complete": true}

User: "Write a Python function"
Output: {"action": "call_agent", "agent_id": "coder", "input": "Write a Python function...", "is_complete": false}

Available agents: researcher, coder, writer, social
Available tools: search.web, file.read, file.write, calculator.compute"""
    
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
        
        # DEBUG: Log the raw LLM response
        logger.info(
            "Orchestrator raw LLM response",
            response_content=response.content[:500],
            response_length=len(response.content)
        )
        
        # Parse decision
        decision = self._parse_decision(response.content)
        
        # DEBUG: Log the parsed decision
        logger.info(
            "Orchestrator parsed decision",
            agent_id=self.agent_id,
            action=decision.get("action"),
            input_field=decision.get("input", "")[:100],
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
        # If content looks like a conversational response (not JSON), use it directly
        if content and not content.strip().startswith('{'):
            logger.info("Using unstructured response as final answer", content_preview=content[:100])
            return {
                "reasoning": "Direct response from orchestrator",
                "action": "final_response",
                "input": content.strip(),
                "is_complete": True
            }
        
        # Default: treat as final response with the content
        return {
            "reasoning": "Failed to parse structured decision",
            "action": "final_response",
            "input": content,
            "is_complete": True
        }