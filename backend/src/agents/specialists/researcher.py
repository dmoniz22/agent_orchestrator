"""Researcher agent for information gathering."""

from typing import Any

from src.agents.base import AgentConfig, BaseAgent
from src.core.logging import get_logger
from src.models.provider import Message

logger = get_logger(__name__)


class ResearcherAgent(BaseAgent):
    """Specialist agent for research tasks.
    
    Handles:
    - Web search and information gathering
    - Content extraction from URLs
    - Information synthesis and summarization
    - Fact checking
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert researcher. Your task is to gather, analyze, and synthesize information from various sources.

Capabilities:
1. Search the web for current information
2. Extract and summarize content from URLs
3. Synthesize information from multiple sources
4. Fact-check claims and provide evidence
5. Create comprehensive research reports

Guidelines:
- Always cite your sources
- Distinguish between facts and opinions
- Note the date/relevance of information
- Synthesize don't just summarize
- Identify gaps in available information

When researching:
1. Plan your search strategy
2. Evaluate source credibility
3. Cross-reference information across sources
4. Synthesize findings into coherent answers
5. Present information objectively

When you don't have access to search results:
- Clearly state what information you would search for
- Explain what sources would be most relevant
- Provide the best answer based on your training data
- Note any limitations"""
    
    async def run(
        self,
        input_text: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """Execute research task.
        
        Args:
            input_text: Research query or topic.
            context: Optional context with search results, URLs, etc.
            
        Returns:
            Research findings and synthesis.
        """
        logger.info(
            "Researcher agent processing query",
            agent_id=self.agent_id,
            query=input_text[:100]
        )
        
        # Build prompt with context
        system_prompt = self._build_system_prompt(context)
        
        # Get response from model
        messages = self.build_messages(system_prompt, input_text)
        
        response = await self.generate(
            messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        logger.info(
            "Researcher agent completed query",
            agent_id=self.agent_id,
            response_length=len(response.content)
        )
        
        return response.content
    
    def _build_system_prompt(self, context: dict[str, Any] | None) -> str:
        """Build system prompt with research context.
        
        Args:
            context: Optional context with search results, etc.
            
        Returns:
            Complete system prompt.
        """
        base_prompt = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        if not context:
            return base_prompt
        
        lines = [base_prompt]
        
        # Add search results if available
        if "search_results" in context:
            lines.append("\nSearch results:")
            for i, result in enumerate(context["search_results"][:5], 1):
                lines.append(f"\n{i}. {result.get('title', 'Untitled')}")
                lines.append(f"   URL: {result.get('url', 'N/A')}")
                lines.append(f"   Snippet: {result.get('snippet', 'No snippet')}")
        
        # Add scraped content if available
        if "scraped_content" in context:
            lines.append("\nContent from URL:")
            lines.append(f"URL: {context.get('url', 'N/A')}")
            lines.append("Content:")
            # Limit content length
            content = context["scraped_content"]
            if len(content) > 8000:
                content = content[:8000] + "\n... [content truncated]"
            lines.append(content)
        
        # Add research focus if specified
        if "focus" in context:
            lines.append(f"\nResearch focus: {context['focus']}")
        
        return "\n".join(lines)