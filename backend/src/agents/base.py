"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.exceptions import AgentError
from src.core.logging import get_logger
from src.models.provider import Message, ModelProvider, ModelResponse

logger = get_logger(__name__)


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    model: str = Field(default="llama3.1:8b", description="Model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    system_prompt: str = Field(default="", description="System prompt template")
    allowed_tools: list[str] = Field(default_factory=list)
    max_steps: int = Field(default=10, ge=1)


class BaseAgent(ABC):
    """Abstract base class for all agents.
    
    Provides common functionality for:
    - Configuration management
    - Prompt template rendering
    - Tool invocation
    - Model interaction
    """
    
    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        model_provider: ModelProvider | None = None
    ) -> None:
        """Initialize base agent.
        
        Args:
            agent_id: Unique agent identifier.
            config: Agent configuration.
            model_provider: Model provider for LLM calls.
        """
        self.agent_id = agent_id
        self.config = config
        self.model_provider = model_provider
        
        logger.info(
            "Agent initialized",
            agent_id=agent_id,
            name=config.name,
            model=config.model
        )
    
    @abstractmethod
    async def run(
        self,
        input_text: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """Execute the agent.
        
        Args:
            input_text: Input query or task.
            context: Optional execution context.
            
        Returns:
            Agent response.
        """
        pass
    
    async def generate(
        self,
        messages: list[Message],
        tools: list | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None
    ) -> ModelResponse:
        """Generate response using model provider.
        
        Args:
            messages: Conversation messages.
            tools: Optional tools for function calling.
            temperature: Override temperature.
            max_tokens: Override max tokens.
            
        Returns:
            Model response.
            
        Raises:
            AgentError: If model provider not configured.
        """
        if not self.model_provider:
            raise AgentError(
                message="Model provider not configured",
                agent_id=self.agent_id
            )
        
        temp = temperature or self.config.temperature
        tokens = max_tokens or self.config.max_tokens
        
        logger.debug(
            "Generating response",
            agent_id=self.agent_id,
            message_count=len(messages),
            has_tools=tools is not None
        )
        
        try:
            response = await self.model_provider.generate(
                messages=messages,
                model=self.config.model,
                tools=tools,
                temperature=temp,
                max_tokens=tokens
            )
            
            logger.debug(
                "Response generated",
                agent_id=self.agent_id,
                content_length=len(response.content),
                finish_reason=response.finish_reason
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Generation failed",
                agent_id=self.agent_id,
                error=str(e)
            )
            raise AgentError(
                message=f"Failed to generate response: {e}",
                agent_id=self.agent_id
            ) from e
    
    def render_prompt(
        self,
        template: str,
        variables: dict[str, Any]
    ) -> str:
        """Render a prompt template with variables.
        
        Args:
            template: Prompt template with {variable} placeholders.
            variables: Values to substitute.
            
        Returns:
            Rendered prompt.
        """
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(
                "Missing template variable",
                agent_id=self.agent_id,
                variable=str(e)
            )
            # Return template with available variables
            return template.format(**{k: v for k, v in variables.items() if k in template})
    
    def build_messages(
        self,
        system_prompt: str | None,
        user_input: str,
        history: list[Message] | None = None
    ) -> list[Message]:
        """Build message list for model.
        
        Args:
            system_prompt: System instruction.
            user_input: User query.
            history: Optional conversation history.
            
        Returns:
            List of messages.
        """
        messages: list[Message] = []
        
        # Add system prompt
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        
        # Add history
        if history:
            messages.extend(history)
        
        # Add user input
        messages.append(Message(role="user", content=user_input))
        
        return messages
    
    def can_use_tool(self, tool_id: str) -> bool:
        """Check if agent can use a tool.
        
        Args:
            tool_id: Tool identifier.
            
        Returns:
            True if agent can use the tool.
        """
        if not self.config.allowed_tools:
            return True  # No restrictions
        return tool_id in self.config.allowed_tools
    
    def get_info(self) -> dict[str, Any]:
        """Get agent information.
        
        Returns:
            Agent metadata.
        """
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "description": self.config.description,
            "model": self.config.model,
            "allowed_tools": self.config.allowed_tools,
            "max_steps": self.config.max_steps
        }
