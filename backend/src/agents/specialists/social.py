"""Social agent for social media operations."""

from typing import Any

from src.agents.base import AgentConfig, BaseAgent
from src.core.logging import get_logger
from src.models.provider import Message

logger = get_logger(__name__)


class SocialAgent(BaseAgent):
    """Specialist agent for social media tasks.
    
    Handles:
    - Social media content creation
    - Tweet/thread composition
    - LinkedIn posts
    - GitHub issue/PR descriptions
    - Social media strategy
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are a social media expert. Your task is to create engaging social media content and manage social operations.

Capabilities:
1. Write tweets and Twitter threads
2. Create LinkedIn posts
3. Draft GitHub issues and PR descriptions
4. Develop social media content strategies
5. Engage with communities professionally

Guidelines:
- Keep content concise and engaging
- Use appropriate hashtags and mentions
- Match the platform's style and culture
- Maintain professional tone for work accounts
- Consider timing and context

Platform-specific:

Twitter/X:
- Max 280 chars per tweet
- Use threads for longer content
- Engage with relevant hashtags
- Be conversational but professional

LinkedIn:
- Professional, business-focused
- Longer-form content acceptable
- Share insights and expertise
- Engage with industry topics

GitHub:
- Clear, technical descriptions
- Include reproduction steps for bugs
- Reference related issues/PRs
- Follow project conventions

When creating content:
1. Know the platform and audience
2. Hook readers with opening line
3. Provide value or entertainment
4. Include clear calls-to-action
5. Use appropriate formatting"""
    
    async def run(
        self,
        input_text: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """Execute social media task.
        
        Args:
            input_text: Task description or content to create/edit.
            context: Optional context with platform, style, constraints, etc.
            
        Returns:
            Created or edited social content.
        """
        logger.info(
            "Social agent processing task",
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
            "Social agent completed task",
            agent_id=self.agent_id,
            response_length=len(response.content)
        )
        
        return response.content
    
    def _build_system_prompt(self, context: dict[str, Any] | None) -> str:
        """Build system prompt with social context.
        
        Args:
            context: Optional context with platform, etc.
            
        Returns:
            Complete system prompt.
        """
        base_prompt = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        if not context:
            return base_prompt
        
        lines = [base_prompt]
        
        # Add platform
        if "platform" in context:
            lines.append(f"\nTarget platform: {context['platform']}")
        
        # Add account type
        if "account_type" in context:
            lines.append(f"Account type: {context['account_type']}")
        
        # Add character limit
        if "char_limit" in context:
            lines.append(f"Character limit: {context['char_limit']}")
        
        # Add required hashtags
        if "hashtags" in context:
            lines.append(f"Required hashtags: {', '.join(context['hashtags'])}")
        
        # Add mentions
        if "mentions" in context:
            lines.append(f"Include mentions: {', '.join(context['mentions'])}")
        
        # Add content to repurpose
        if "source_content" in context:
            lines.append("\nSource content to repurpose:")
            lines.append(context["source_content"])
        
        # Add link to include
        if "link" in context:
            lines.append(f"\nInclude link: {context['link']}")
        
        return "\n".join(lines)