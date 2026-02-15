"""Health check endpoints."""

from fastapi import APIRouter, status
from pydantic import BaseModel

from src.core.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    message: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.
    
    Returns:
        Health status.
    """
    settings = get_settings()
    
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        message="OMNI API is running"
    )


@router.get("/")
async def root() -> dict:
    """Root endpoint.
    
    Returns:
        API information.
    """
    return {
        "name": "OMNI API",
        "version": "0.1.0",
        "description": "Ollama Multi-agent Network Interface",
        "docs": "/docs"
    }
