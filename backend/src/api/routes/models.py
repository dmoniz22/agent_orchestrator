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


class ModelListResponse(BaseModel):
    """Model list response."""
    models: List[ModelInfo]
    default_model: str
    fallback_model: str | None = None


@router.get("/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """List available Ollama models.
    
    Returns:
        List of available models.
    """
    settings = get_settings()
    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        default_model="llama3.1:8b"
    )
    
    try:
        model_names = await provider.list_models()
        models = [
            ModelInfo(name=name, description=f"Ollama model: {name}")
            for name in model_names
        ]
        
        return ModelListResponse(
            models=models,
            default_model="llama3.1:8b",
            fallback_model="qwen2.5-coder:14b"
        )
    except Exception as e:
        # If Ollama is not available, return configured models
        return ModelListResponse(
            models=[
                ModelInfo(name="llama3.1:8b", description="Default model")
            ],
            default_model="llama3.1:8b",
            fallback_model="qwen2.5-coder:14b"
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
    
    return {
        "name": model_name,
        "base_url": settings.ollama.base_url,
        "available": True
    }