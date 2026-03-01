"""Model providers for OMNI.

This module provides unified access to multiple LLM providers:
- Ollama: Local models (free, private, no API key needed)
- OpenRouter: Cloud models (100+ models including Claude, GPT-4o, Gemini)
- FallbackProvider: Automatically routes between local and cloud with failover

Usage:
    from src.models import get_fallback_provider, ModelResponse
    
    provider = get_fallback_provider()
    response = await provider.generate(
        messages=[Message(role="user", content="Hello")],
        model="claude-sonnet"  # Automatically uses OpenRouter
    )
    
    # For local models, automatically uses Ollama
    response = await provider.generate(
        messages=[Message(role="user", content="Hello")],
        model="llama3.1:8b"  # Automatically uses Ollama
    )
"""

from .provider import Message, ModelProvider, ModelResponse, ToolSchema
from .ollama import OllamaProvider, OllamaProviderFactory
from .openrouter import OpenRouterProvider, OpenRouterProviderFactory
from .fallback import FallbackProvider, FallbackProviderFactory

__all__ = [
    # Base classes
    "Message",
    "ModelProvider", 
    "ModelResponse",
    "ToolSchema",
    # Ollama (local)
    "OllamaProvider",
    "OllamaProviderFactory",
    # OpenRouter (cloud)
    "OpenRouterProvider",
    "OpenRouterProviderFactory",
    # Fallback (automatic routing)
    "FallbackProvider",
    "FallbackProviderFactory",
    # Convenience functions
    "get_ollama_provider",
    "get_openrouter_provider",
    "get_fallback_provider",
    "create_provider_from_config",
]


# Global provider instances (singletons)
_ollama_provider: OllamaProvider | None = None
_openrouter_provider: OpenRouterProvider | None = None
_fallback_provider: FallbackProvider | None = None


def get_ollama_provider(
    base_url: str = "http://localhost:11434",
    default_model: str = "llama3.1:8b"
) -> OllamaProvider:
    """Get or create the global Ollama provider instance.
    
    Args:
        base_url: Ollama server URL
        default_model: Default model to use
        
    Returns:
        OllamaProvider singleton
    """
    global _ollama_provider
    if _ollama_provider is None:
        _ollama_provider = OllamaProvider(
            base_url=base_url,
            default_model=default_model
        )
    return _ollama_provider


def get_openrouter_provider(
    api_key: str | None = None,
    default_model: str = "anthropic/claude-3-haiku-20240307"
) -> OpenRouterProvider | None:
    """Get or create the global OpenRouter provider instance.
    
    Args:
        api_key: OpenRouter API key (auto-loads from env if not provided)
        default_model: Default model to use
        
    Returns:
        OpenRouterProvider singleton, or None if no API key
    """
    global _openrouter_provider
    
    if _openrouter_provider is None:
        if api_key is None:
            import os
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
        
        if not api_key:
            return None
            
        _openrouter_provider = OpenRouterProvider(
            api_key=api_key,
            default_model=default_model
        )
    
    return _openrouter_provider


def get_fallback_provider(
    ollama_url: str = "http://localhost:11434",
    ollama_default_model: str = "llama3.1:8b",
    openrouter_api_key: str | None = None,
    openrouter_default_model: str = "anthropic/claude-3-haiku-20240307",
    prefer_local: bool = True,
    fallback_on_error: bool = True
) -> FallbackProvider:
    """Get or create the global fallback provider instance.
    
    This is the recommended way to use providers in OMNI. It automatically:
    - Routes local models to Ollama
    - Routes cloud models to OpenRouter
    - Falls back to OpenRouter if Ollama fails
    
    Args:
        ollama_url: Ollama server URL
        ollama_default_model: Default Ollama model
        openrouter_api_key: OpenRouter API key (auto-loads from env if not provided)
        openrouter_default_model: Default OpenRouter model
        prefer_local: Try local models first
        fallback_on_error: Automatically fallback on errors
        
    Returns:
        FallbackProvider singleton with automatic routing
        
    Example:
        provider = get_fallback_provider()
        
        # This uses Ollama (local)
        response = await provider.generate(messages, "llama3.1:8b")
        
        # This uses OpenRouter (cloud)
        response = await provider.generate(messages, "claude-sonnet")
        
        # Check which provider was used
        print(f"Used: {provider.last_provider_used}")
    """
    global _fallback_provider
    
    if _fallback_provider is None:
        if openrouter_api_key is None:
            import os
            openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        
        _fallback_provider = FallbackProvider(
            ollama_url=ollama_url,
            ollama_default_model=ollama_default_model,
            openrouter_api_key=openrouter_api_key,
            openrouter_default_model=openrouter_default_model,
            prefer_local=prefer_local,
            fallback_on_error=fallback_on_error
        )
    
    return _fallback_provider


def create_provider_from_config(config: dict) -> ModelProvider:
    """Create a provider from configuration dictionary.
    
    Supports creating OllamaProvider, OpenRouterProvider, or FallbackProvider.
    
    Args:
        config: Configuration dictionary with provider settings
        
    Returns:
        Configured ModelProvider instance
        
    Example:
        # Create fallback provider
        provider = create_provider_from_config({
            "type": "fallback",
            "ollama_url": "http://localhost:11434",
            "openrouter_api_key": "sk-or-..."
        })
        
        # Create Ollama only
        provider = create_provider_from_config({
            "type": "ollama",
            "base_url": "http://localhost:11434"
        })
    """
    provider_type = config.get("type", "ollama").lower()
    
    if provider_type == "ollama":
        return OllamaProviderFactory.create(config)
    elif provider_type == "openrouter":
        return OpenRouterProviderFactory.create(config)
    elif provider_type == "fallback":
        return FallbackProviderFactory.create(config)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def reset_providers() -> None:
    """Reset all provider singletons.
    
    Call this when configuration changes or for testing.
    """
    global _ollama_provider, _openrouter_provider, _fallback_provider
    
    if _ollama_provider:
        import asyncio
        asyncio.run(_ollama_provider.close())
    if _openrouter_provider:
        import asyncio
        asyncio.run(_openrouter_provider.close())
    if _fallback_provider:
        import asyncio
        asyncio.run(_fallback_provider.close())
    
    _ollama_provider = None
    _openrouter_provider = None
    _fallback_provider = None
