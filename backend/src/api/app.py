"""FastAPI application for OMNI API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.logging import get_logger
from .routes import agents, health, tasks, tools

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app.
    """
    settings = get_settings()
    
    app = FastAPI(
        title="OMNI API",
        description="Ollama Multi-agent Network Interface",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(tools.router, prefix="/api/v1/tools", tags=["Tools"])
    
    logger.info("FastAPI application created")
    
    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler.
    
    Args:
        app: FastAPI application.
        
    Yields:
        None
    """
    # Startup
    logger.info("Starting up OMNI API")
    
    # TODO: Initialize database connections
    # TODO: Load agent and tool registries
    
    yield
    
    # Shutdown
    logger.info("Shutting down OMNI API")
    
    # TODO: Close database connections


# Create application instance
app = create_app()
