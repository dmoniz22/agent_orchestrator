"""Fallback provider that combines Ollama (primary) with OpenRouter (fallback)."""

from typing import Any, AsyncIterator

import httpx

from ..core.exceptions import ProviderError
from ..core.logging import get_logger
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider
from .provider import Message, ModelProvider, ModelResponse, ToolSchema

logger = get_logger(__name__)


class FallbackProvider(ModelProvider):
    """Combined provider with automatic fallback from Ollama to OpenRouter.
    
    This provider tries Ollama first (local, free, private), and if it fails,
    automatically falls back to OpenRouter (cloud, paid, external).
    
    Usage:
        provider = FallbackProvider(
            ollama_url="http://localhost:11434",
            openrouter_api_key="sk-or-..."
        )
        response = await provider.generate(messages, "claude-sonnet")
    
    The model name determines which provider to use:
    - Local models (llama3.1, qwen2.5, etc.) -> Ollama
    - Cloud models (claude-opus, gpt-4o, etc.) -> OpenRouter
    - Or explicitly: provider = FallbackProvider(primary="ollama", secondary="openrouter")
    """
    
    # Models that should use OpenRouter (not available locally)
    CLOUD_MODELS = {
        "claude-opus", "claude-sonnet", "claude-haiku",
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5",
        "gemini-pro", "gemini-flash",
        "mistral-large", "mistral-medium", "mistral-small",
        "deepseek-chat", "deepseek-coder",
        "llama-3.1-70b", "llama-3.1-8b",
    }
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        ollama_default_model: str = "llama3.1:8b",
        openrouter_api_key: str | None = None,
        openrouter_default_model: str = "anthropic/claude-3-haiku-20240307",
        prefer_local: bool = True,
        fallback_on_error: bool = True,
    ):
        """Initialize fallback provider.
        
        Args:
            ollama_url: Ollama server URL
            ollama_default_model: Default Ollama model
            openrouter_api_key: OpenRouter API key (required for fallback)
            openrouter_default_model: Default OpenRouter model
            prefer_local: Try local models first if they match
            fallback_on_error: Automatically fallback on any error
        """
        super().__init__("fallback", "combined")
        self.ollama = OllamaProvider(
            base_url=ollama_url,
            default_model=ollama_default_model
        )
        self.openrouter = OpenRouterProvider(
            api_key=openrouter_api_key or "",
            default_model=openrouter_default_model
        ) if openrouter_api_key else None
        self.prefer_local = prefer_local
        self.fallback_on_error = fallback_on_error
        self._last_provider_used: str | None = None
        
    def _choose_provider(self, model: str) -> tuple[ModelProvider, str]:
        """Choose which provider to use based on model name.
        
        Returns:
            Tuple of (provider, provider_name)
        """
        model_lower = model.lower()
        
        # Check if it's a known cloud model
        for cloud_model in self.CLOUD_MODELS:
            if cloud_model in model_lower:
                if self.openrouter:
                    return self.openrouter, "openrouter"
                else:
                    logger.warning(f"Cloud model {model} requested but OpenRouter not configured")
                    return self.ollama, "ollama"
        
        # Default: try Ollama first if prefer_local is True
        if self.prefer_local:
            return self.ollama, "ollama"
        
        return self.ollama, "ollama"
    
    async def _generate_with_fallback(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolSchema] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        format: str | None = None
    ) -> ModelResponse:
        """Generate with automatic fallback on failure."""
        
        # First try: primary provider
        provider, provider_name = self._choose_provider(model)
        self._last_provider_used = provider_name
        
        logger.info(
            "Attempting generation",
            model=model,
            provider=provider_name,
            prefer_local=self.prefer_local
        )
        
        try:
            response = await provider.generate(
                messages=messages,
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
                format=format
            )
            logger.info(f"Generation successful with {provider_name}", model=model)
            return response
            
        except Exception as primary_error:
            logger.warning(
                f"Primary provider ({provider_name}) failed",
                error=str(primary_error),
                model=model
            )
            
            # Check if we can fallback
            if not self.fallback_on_error:
                raise primary_error
            
            # Try secondary provider (OpenRouter)
            if provider_name == "ollama" and self.openrouter:
                logger.info(f"Falling back to OpenRouter for model {model}")
                self._last_provider_used = "openrouter"
                
                try:
                    response = await self.openrouter.generate(
                        messages=messages,
                        model=model,
                        tools=tools,
                        tool_choice=tool_choice,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        format=format
                    )
                    logger.info("Generation successful with OpenRouter fallback", model=model)
                    return response
                    
                except Exception as fallback_error:
                    logger.error(
                        "Fallback also failed",
                        error=str(fallback_error),
                        model=model
                    )
                    raise ProviderError(
                        f"Both primary and fallback failed: {primary_error}, {fallback_error}",
                        provider="fallback"
                    ) from primary_error
            
            # No fallback available, raise original error
            raise primary_error
    
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
        """Generate response with automatic fallback."""
        return await self._generate_with_fallback(
            messages, model, tools, tool_choice, temperature, max_tokens, format
        )
    
    async def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """Stream response (no fallback for streaming currently)."""
        provider, provider_name = self._choose_provider(model)
        
        if provider_name == "ollama":
            async for chunk in self.ollama.stream(messages, model, temperature, max_tokens):
                yield chunk
        else:
            async for chunk in self.openrouter.stream(messages, model, temperature, max_tokens):
                yield chunk
    
    async def list_models(self) -> list[str]:
        """List models from both providers."""
        models = []
        
        # Get Ollama models
        try:
            ollama_models = await self.ollama.list_models()
            models.extend([f"ollama:{m}" for m in ollama_models])
        except Exception as e:
            logger.warning(f"Could not list Ollama models: {e}")
        
        # Get OpenRouter models
        if self.openrouter:
            try:
                openrouter_models = await self.openrouter.list_models()
                models.extend([f"openrouter:{m}" for m in openrouter_models])
            except Exception as e:
                logger.warning(f"Could not list OpenRouter models: {e}")
        
        return models
    
    async def health_check(self) -> bool:
        """Check health of both providers."""
        ollama_healthy = await self.ollama.health_check()
        openrouter_healthy = await self.openrouter.health_check() if self.openrouter else False
        
        logger.info(
            "Health check",
            ollama=ollama_healthy,
            openrouter=openrouter_healthy
        )
        
        # Consider healthy if at least one provider works
        return ollama_healthy or openrouter_healthy
    
    async def embed(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        """Generate embeddings (delegates to Ollama)."""
        return await self.ollama.embed(text, model)
    
    @property
    def last_provider_used(self) -> str | None:
        """Get the name of the provider used in the last request."""
        return self._last_provider_used
    
    @property
    def is_using_cloud(self) -> bool:
        """Check if currently using cloud (OpenRouter) fallback."""
        return self._last_provider_used == "openrouter"
    
    async def close(self) -> None:
        """Close both providers."""
        await self.ollama.close()
        if self.openrouter:
            await self.openrouter.close()


class FallbackProviderFactory:
    """Factory for creating FallbackProvider instances."""
    
    @staticmethod
    def create(config: dict[str, Any]) -> FallbackProvider:
        """Create FallbackProvider from configuration."""
        return FallbackProvider(
            ollama_url=config.get("ollama_base_url", "http://localhost:11434"),
            ollama_default_model=config.get("ollama_default_model", "llama3.1:8b"),
            openrouter_api_key=config.get("openrouter_api_key"),
            openrouter_default_model=config.get("openrouter_default_model", "anthropic/claude-3-haiku-20240307"),
            prefer_local=config.get("prefer_local", True),
            fallback_on_error=config.get("fallback_on_error", True),
        )