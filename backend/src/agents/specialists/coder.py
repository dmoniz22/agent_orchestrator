"""Coder agent for code generation and execution."""

from typing import Any

from src.agents.base import AgentConfig, BaseAgent
from src.core.logging import get_logger
from src.models.provider import Message

logger = get_logger(__name__)


class CoderAgent(BaseAgent):
    """Specialist agent for code tasks.
    
    Handles:
    - Code generation and completion
    - Code review and analysis
    - Bug fixing and refactoring
    - GitHub operations (if tools available)
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert software engineer. Your task is to write, review, and analyze code.

Capabilities:
1. Write clean, well-documented code
2. Review code for bugs, security issues, and best practices
3. Explain complex code in simple terms
4. Refactor code for better performance or readability

Guidelines:
- Always provide complete, runnable code
- Include comments explaining complex logic
- Consider edge cases and error handling
- Follow language-specific best practices
- If modifying existing code, show the complete updated version

When writing code:
1. Understand the requirements clearly
2. Choose appropriate data structures and algorithms
3. Write clean, maintainable code
4. Add error handling where needed
5. Include usage examples if helpful

When reviewing code:
1. Check for bugs and logical errors
2. Look for security vulnerabilities
3. Assess code quality and maintainability
4. Suggest specific improvements with examples"""
    
    async def run(
        self,
        input_text: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """Execute coding task.
        
        Args:
            input_text: Code task description or code to review.
            context: Optional context with file contents, language, etc.
            
        Returns:
            Generated code, review, or analysis.
        """
        logger.info(
            "Coder agent processing task",
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
            "Coder agent completed task",
            agent_id=self.agent_id,
            response_length=len(response.content)
        )
        
        return response.content
    
    def _build_system_prompt(self, context: dict[str, Any] | None) -> str:
        """Build system prompt with context.
        
        Args:
            context: Optional context with code, language, etc.
            
        Returns:
            Complete system prompt.
        """
        base_prompt = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        if not context:
            return base_prompt
        
        lines = [base_prompt]
        
        # Add language if specified
        if "language" in context:
            lines.append(f"\nTarget language: {context['language']}")
        
        # Add existing code if provided
        if "existing_code" in context:
            lines.append("\nExisting code to work with:")
            lines.append(f"```{context.get('language', 'python')}")
            lines.append(context["existing_code"])
            lines.append("```")
        
        # Add file path if provided
        if "file_path" in context:
            lines.append(f"\nFile path: {context['file_path']}")
        
        return "\n".join(lines)