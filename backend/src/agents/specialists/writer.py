"""Writer agent for content creation."""

from typing import Any

from src.agents.base import AgentConfig, BaseAgent
from src.core.logging import get_logger
from src.models.provider import Message

logger = get_logger(__name__)


class WriterAgent(BaseAgent):
    """Specialist agent for writing tasks.
    
    Handles:
    - Blog posts and articles
    - Documentation and tutorials
    - Marketing copy
    - Email and communication
    - Creative writing
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert writer. Your task is to create high-quality written content.

Capabilities:
1. Write blog posts and articles
2. Create documentation and tutorials
3. Draft marketing copy and emails
4. Edit and improve existing content
5. Adapt tone for different audiences

Guidelines:
- Write clear, engaging content
- Structure content logically with headings
- Use appropriate tone for the audience
- Include calls-to-action where relevant
- Proofread for grammar and clarity

When writing:
1. Understand the target audience
2. Establish the purpose and tone
3. Create an outline if needed
4. Write engaging introductions
5. Use examples and specifics
6. End with clear conclusions

When editing:
1. Improve clarity and flow
2. Fix grammar and spelling
3. Enhance readability
4. Ensure consistent tone
5. Provide specific suggestions"""
    
    async def run(
        self,
        input_text: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """Execute writing task.
        
        Args:
            input_text: Writing task description or content to edit.
            context: Optional context with style, audience, format, etc.
            
        Returns:
            Written or edited content.
        """
        logger.info(
            "Writer agent processing task",
            agent_id=self.agent_id,
            task=input_text[:100]
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
            "Writer agent completed task",
            agent_id=self.agent_id,
            response_length=len(response.content)
        )
        
        return response.content
    
    def _build_system_prompt(self, context: dict[str, Any] | None) -> str:
        """Build system prompt with writing context.
        
        Args:
            context: Optional context with style, audience, etc.
            
        Returns:
            Complete system prompt.
        """
        base_prompt = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        if not context:
            return base_prompt
        
        lines = [base_prompt]
        
        # Add content type
        if "content_type" in context:
            lines.append(f"\nContent type: {context['content_type']}")
        
        # Add target audience
        if "audience" in context:
            lines.append(f"Target audience: {context['audience']}")
        
        # Add tone/style
        if "tone" in context:
            lines.append(f"Tone: {context['tone']}")
        
        # Add format guidelines
        if "format" in context:
            lines.append(f"Format: {context['format']}")
        
        # Add length guidelines
        if "length" in context:
            lines.append(f"Length: {context['length']}")
        
        # Add existing content to edit
        if "existing_content" in context:
            lines.append("\nContent to edit:")
            lines.append(context["existing_content"])
        
        # Add specific requirements
        if "requirements" in context:
            lines.append("\nSpecific requirements:")
            for req in context["requirements"]:
                lines.append(f"- {req}")
        
        return "\n".join(lines)