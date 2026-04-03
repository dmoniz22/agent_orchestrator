"""Model management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from src.core.config import get_settings
from src.models.ollama import OllamaProvider

router = APIRouter()


class ModelInfo(BaseModel):
    """Model information."""

    name: str
    description: str = ""
    size: str = ""
    provider: str = "ollama"


class ModelListResponse(BaseModel):
    """Model list response."""

    models: List[ModelInfo]
    default_model: str
    fallback_model: str | None = None
    openrouter_configured: bool = False
    openrouter_models: List[str] = []


@router.get("/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """List available Ollama and OpenRouter models.

    Returns:
        List of available models.
    """
    settings = get_settings()
    provider = OllamaProvider(
        base_url=settings.ollama_base_url, default_model=settings.ollama_default_model
    )

    ollama_models = []
    try:
        model_names = await provider.list_models()
        ollama_models = [
            ModelInfo(name=name, description=f"Local Ollama model", provider="ollama")
            for name in model_names
        ]
        await provider.close()
    except Exception:
        ollama_models = [
            ModelInfo(
                name=settings.ollama_default_model,
                description="Default model (Ollama unavailable)",
                provider="ollama",
            )
        ]

    # Check OpenRouter configuration
    openrouter_configured = bool(settings.openrouter_api_key)
    openrouter_models = []
    if openrouter_configured:
        openrouter_models = [
            "anthropic/claude-3-haiku-20240307",
            "anthropic/claude-3-sonnet-20240229",
            "anthropic/claude-3-opus-20240229",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-pro-1.5",
            "google/gemini-flash-1.5",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-large",
            "deepseek/deepseek-coder",
        ]

    return ModelListResponse(
        models=ollama_models,
        default_model=settings.ollama_default_model,
        fallback_model=settings.openrouter_default_model if openrouter_configured else None,
        openrouter_configured=openrouter_configured,
        openrouter_models=openrouter_models,
    )


@router.get("/models/{model_name}")
async def get_model_info(model_name: str) -> dict:
    """Get information about a specific model.

    Args:
        model_name: Name of the model.

    Returns:
        Model information.
    """
    settings = get_settings()

    return {"name": model_name, "base_url": settings.ollama_base_url, "available": True}
