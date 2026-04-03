"""Health check endpoints."""

from fastapi import APIRouter, status
from pydantic import BaseModel

from src.core.config import get_settings
from src.db.session import test_connection
from src.models.ollama import OllamaProvider

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    message: str
    checks: dict[str, bool] = {}


class DetailedHealthResponse(BaseModel):
    """Detailed health check response with service status."""

    status: str
    version: str
    message: str
    checks: dict[str, dict[str, bool | str]]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health status.
    """
    settings = get_settings()

    return HealthResponse(status="healthy", version="0.1.0", message="OMNI API is running")


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check with database and service connectivity.

    Returns:
        Detailed health status including external service checks.
    """
    settings = get_settings()
    checks: dict[str, dict[str, bool | str]] = {}

    # Check database
    db_healthy = await test_connection()
    checks["database"] = {
        "healthy": db_healthy,
        "host": settings.database.host,
        "port": str(settings.database.port),
        "database": settings.database.name,
    }

    # Check Ollama
    ollama = OllamaProvider(base_url=settings.ollama_base_url)
    ollama_healthy = await ollama.health_check()
    await ollama.close()
    checks["ollama"] = {
        "healthy": ollama_healthy,
        "url": settings.ollama_base_url,
    }

    # Overall status
    all_healthy = db_healthy and ollama_healthy
    overall_status = "healthy" if all_healthy else "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        version="0.1.0",
        message="OMNI API is running" if all_healthy else "Some services are unavailable",
        checks=checks,
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
        "docs": "/docs",
    }
