"""Model provider abstract base class."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A message in the conversation."""
    
    role: str = Field(..., description="Message role (system, user, assistant, tool)")
    content: str = Field(..., description="Message content")
    name: str | None = Field(default=None, description="Tool name for tool messages")
    tool_call_id: str | None = Field(default=None, description="ID of tool call")


class ToolSchema(BaseModel):
    """Schema for a tool/function."""
    
    type: str = Field(default="function", description="Tool type")
    function: dict[str, Any] = Field(..., description="Function definition")


class ModelResponse(BaseModel):
    """Response from the model provider."""
    
    content: str | None = Field(default=None, description="Generated content")
    role: str = Field(default="assistant", description="Response role")
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Tool calls requested by model"
    )
    model: str = Field(..., description="Model used for generation")
    usage: dict[str, int] | None = Field(
        default=None,
        description="Token usage information"
    )
    finish_reason: str | None = Field(
        default=None,
        description="Reason for finishing generation"
    )


class ModelProvider(ABC):
    """Abstract base class for LLM providers.
    
    All model providers must implement this interface to be used
    by the orchestration system.
    """
    
    def __init__(self, provider_id: str, base_url: str | None = None) -> None:
        """Initialize the provider.
        
        Args:
            provider_id: Unique identifier for this provider.
            base_url: Optional base URL for the provider API.
        """
        self.provider_id = provider_id
        self.base_url = base_url
    
    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolSchema] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        format: str | None = None
    ) -> ModelResponse:
        """Generate a response from the model.
        
        Args:
            messages: List of messages in the conversation.
            model: Model identifier to use.
            tools: Optional list of tools the model can call.
            tool_choice: Optional tool selection strategy.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens to generate.
            format: Optional output format (e.g., "json").
            
        Returns:
            ModelResponse with generated content.
            
        Raises:
            ProviderError: If generation fails.
        """
        ...
    
    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """Stream a response from the model.
        
        Args:
            messages: List of messages in the conversation.
            model: Model identifier to use.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens to generate.
            
        Yields:
            String chunks of the generated response.
            
        Raises:
            ProviderError: If streaming fails.
        """
        ...
        yield ""
    
    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models.
        
        Returns:
            List of model identifiers.
            
        Raises:
            ProviderError: If listing fails.
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy.
        
        Returns:
            True if provider is available, False otherwise.
        """
        ...
    
    async def embed(
        self,
        text: str,
        model: str = "nomic-embed-text"
    ) -> list[float]:
        """Generate embeddings for text.
        
        Args:
            text: Text to embed.
            model: Embedding model to use.
            
        Returns:
            List of embedding values.
            
        Raises:
            ProviderError: If embedding fails.
        """
        # Default implementation - providers should override
        raise NotImplementedError("Embeddings not supported by this provider")