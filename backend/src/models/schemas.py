"""Pydantic schemas for models module."""

from enum import Enum as PyEnum
from typing import Any

from pydantic import BaseModel, Field


class ModelCapability(str, PyEnum):
    """Model capabilities."""
    
    CHAT = "chat"
    COMPLETION = "completion"
    TOOLS = "tools"
    VISION = "vision"
    EMBEDDINGS = "embeddings"


class ModelInfo(BaseModel):
    """Information about a model."""
    
    name: str = Field(..., description="Model identifier")
    description: str | None = Field(default=None, description="Model description")
    context_window: int = Field(default=4096, description="Context window size")
    supports_tools: bool = Field(default=False, description="Whether model supports tool calling")
    capabilities: list[ModelCapability] = Field(
        default_factory=list,
        description="Model capabilities"
    )
    
    class Config:
        """Pydantic config."""
        use_enum_values = True


class ProviderConfig(BaseModel):
    """Configuration for a model provider."""
    
    id: str = Field(..., description="Provider identifier")
    type: str = Field(..., description="Provider type (ollama, openai, etc.)")
    base_url: str = Field(..., description="Provider base URL")
    default_model: str = Field(..., description="Default model to use")
    fallback_model: str | None = Field(default=None, description="Fallback model")
    models: list[ModelInfo] = Field(default_factory=list, description="Available models")
    retry: dict[str, Any] = Field(
        default_factory=lambda: {"max_retries": 3, "base_delay_seconds": 2},
        description="Retry configuration"
    )
    timeout_seconds: int = Field(default=60, description="Request timeout")


class GenerationRequest(BaseModel):
    """Request for text generation."""
    
    messages: list[dict[str, Any]] = Field(..., description="Conversation messages")
    model: str = Field(..., description="Model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    tools: list[dict[str, Any]] | None = Field(default=None)
    tool_choice: str | None = Field(default=None)
    format: str | None = Field(default=None)


class GenerationResponse(BaseModel):
    """Response from text generation."""
    
    content: str | None = Field(default=None)
    tool_calls: list[dict[str, Any]] | None = Field(default=None)
    model: str = Field(...)
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str | None = Field(default=None)


class EmbeddingRequest(BaseModel):
    """Request for text embedding."""
    
    text: str = Field(..., description="Text to embed")
    model: str = Field(default="nomic-embed-text", description="Embedding model")


class EmbeddingResponse(BaseModel):
    """Response from text embedding."""
    
    embedding: list[float] = Field(..., description="Embedding vector")
    model: str = Field(..., description="Model used")
    dimension: int = Field(..., description="Embedding dimension")


class TokenCountRequest(BaseModel):
    """Request for token counting."""
    
    text: str = Field(..., description="Text to count")
    model: str = Field(..., description="Model to use for counting")


class TokenCountResponse(BaseModel):
    """Response with token count."""
    
    count: int = Field(..., description="Token count")
    model: str = Field(..., description="Model used")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    provider: str = Field(..., description="Provider name")
    status: str = Field(..., description="Health status (healthy, unhealthy, unknown)")
    available_models: list[str] = Field(default_factory=list)
    latency_ms: float | None = Field(default=None)