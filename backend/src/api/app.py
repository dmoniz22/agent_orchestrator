"""FastAPI application for OMNI API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.ollama import OllamaProvider
from src.models import FallbackProvider, get_fallback_provider
from src.agents.registry import get_agent_registry
from src.agents.specialists.orchestrator import OrchestratorAgent
from src.agents.specialists.coder import CoderAgent
from src.agents.specialists.researcher import ResearcherAgent
from src.agents.specialists.writer import WriterAgent
from src.agents.specialists.social import SocialAgent
from src.agents.base import AgentConfig
from src.skills.registry import get_tool_registry
from src.skills.library.calculator import CalculatorTool
from src.skills.library.search import SearchTool
from src.skills.library.filesystem import FileReadTool, FileWriteTool
from src.orchestration.engine import get_orchestration_engine
from src.memory.manager import MemoryManager
from src.db.session import init_pool, close_pool
from .routes import (
    agents,
    health,
    models,
    tasks,
    tools,
    tool_management,
    settings as settings_routes,
)
from .middleware.errors import (
    validation_exception_handler,
    pydantic_exception_handler,
    general_exception_handler,
)
from .middleware.rate_limit import RateLimitMiddleware

logger = get_logger(__name__)

# Global model provider (uses fallback between Ollama and OpenRouter)
_model_provider: FallbackProvider | None = None

# Global memory manager
_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """Get or create memory manager."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
        logger.info("Memory manager initialized")
    return _memory_manager


def get_model_provider() -> FallbackProvider:
    """Get or create model provider with Ollama + OpenRouter fallback.

    Uses FallbackProvider to automatically:
    - Route local models (llama3.1, qwen2.5, etc.) to Ollama
    - Route cloud models (claude-*, gpt-*, etc.) to OpenRouter
    - Fallback to OpenRouter if Ollama fails
    """
    global _model_provider
    if _model_provider is None:
        settings = get_settings()

        # Use FallbackProvider with OpenRouter integration
        _model_provider = FallbackProvider(
            ollama_url=settings.ollama_base_url,
            ollama_default_model=settings.ollama_default_model,
            openrouter_api_key=settings.openrouter_api_key,
            openrouter_default_model=settings.openrouter_default_model,
            prefer_local=settings.provider_prefer_local,
            fallback_on_error=settings.provider_fallback_on_error,
        )

        logger.info(
            "Fallback provider initialized",
            ollama_url=settings.ollama_base_url,
            openrouter_configured=bool(settings.openrouter_api_key),
            prefer_local=settings.provider_prefer_local,
        )

    return _model_provider


async def initialize_registries():
    """Initialize agent and tool registries with default items."""
    logger.info("Initializing registries...")

    # Get model provider
    provider = get_model_provider()

    # Initialize agent registry
    agent_registry = get_agent_registry()

    # Register agent classes
    agent_registry.register_agent_class("orchestrator", OrchestratorAgent)
    agent_registry.register_agent_class("coder", CoderAgent)
    agent_registry.register_agent_class("researcher", ResearcherAgent)
    agent_registry.register_agent_class("writer", WriterAgent)
    agent_registry.register_agent_class("social", SocialAgent)

    # Create and register agent instances
    agents_config = {
        "orchestrator": AgentConfig(
            name="Orchestrator",
            description="Routes queries to appropriate specialists",
            model="gemma3:12b",
            temperature=0.1,
        ),
        "coder": AgentConfig(
            name="Coder",
            description="Code generation, review, and analysis",
            model="gemma3:12b",
            temperature=0.2,
            allowed_tools=["calculator.compute", "file.read", "file.write"],
        ),
        "researcher": AgentConfig(
            name="Researcher",
            description="Web research and information synthesis",
            model="gemma3:12b",
            temperature=0.3,
            allowed_tools=["search.web", "calculator.compute"],
        ),
        "writer": AgentConfig(
            name="Writer",
            description="Content creation and editing",
            model="gemma3:12b",
            temperature=0.7,
            allowed_tools=["file.read", "file.write"],
        ),
        "social": AgentConfig(
            name="Social",
            description="Social media content creation",
            model="gemma3:12b",
            temperature=0.8,
        ),
    }

    for agent_id, config in agents_config.items():
        agent_registry.register_config(agent_id, config)
        agent_class = agent_registry._agent_classes.get(agent_id)
        if agent_class:
            agent = agent_class(agent_id=agent_id, config=config, model_provider=provider)
            agent_registry.register_agent(agent_id, agent)
            logger.info(f"Registered agent: {agent_id}")

    # Initialize tool registry
    tool_registry = get_tool_registry()

    # Register tools
    tools = [CalculatorTool(), SearchTool(), FileReadTool(), FileWriteTool()]

    for tool in tools:
        tool_registry.register(tool)
        logger.info(f"Registered tool: {tool.tool_id}")

    # Initialize memory manager
    memory_manager = get_memory_manager()

    # Initialize orchestration engine with orchestrator agent, memory, and registries
    orchestrator = agent_registry.get_agent("orchestrator")
    if orchestrator:
        await get_orchestration_engine(
            orchestrator_agent=orchestrator,
            memory_manager=memory_manager,
            agent_registry=agent_registry,
            tool_registry=tool_registry,
        )
        logger.info("Orchestration engine initialized with registries and memory")

    logger.info("Registries initialized successfully")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    logger.info("Starting up OMNI API")

    # Initialize database pool
    try:
        await init_pool()
        logger.info("Database pool initialized")
    except Exception as e:
        logger.warning("Failed to initialize database pool on startup", error=str(e))

    # Initialize registries
    await initialize_registries()

    yield

    # Shutdown cleanup
    logger.info("Shutting down OMNI API")
    if _model_provider:
        await _model_provider.close()
    if _memory_manager:
        # Clear short-term memory
        pass
    await close_pool()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="OMNI API",
        description="Ollama Multi-agent Network Interface",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware (disabled in development by default)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,
        requests_per_hour=1000,
        burst_limit=10,
    )

    # Add exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(models.router, prefix="/api/v1", tags=["Models"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(tools.router, prefix="/api/v1/tools", tags=["Tools"])
    app.include_router(tool_management.router, prefix="/api/v1", tags=["Tool Management"])
    app.include_router(settings_routes.router, prefix="/api/v1", tags=["Settings"])

    logger.info("FastAPI application created")

    return app


# Create application instance
app = create_app()
