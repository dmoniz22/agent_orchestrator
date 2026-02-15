"""FastAPI application for OMNI API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.ollama import OllamaProvider
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
from .routes import agents, health, models, tasks, tools

logger = get_logger(__name__)

# Global model provider
_model_provider: OllamaProvider | None = None

def get_model_provider() -> OllamaProvider:
    """Get or create model provider."""
    global _model_provider
    if _model_provider is None:
        settings = get_settings()
        _model_provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            default_model="llama3.1:8b",
            fallback_model="qwen2.5-coder:14b"
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
            model="llama3.1:8b",
            temperature=0.1
        ),
        "coder": AgentConfig(
            name="Coder",
            description="Code generation, review, and analysis",
            model="qwen2.5-coder:14b",
            temperature=0.2,
            allowed_tools=["calculator.compute", "file.read", "file.write"]
        ),
        "researcher": AgentConfig(
            name="Researcher",
            description="Web research and information synthesis",
            model="llama3.1:8b",
            temperature=0.3,
            allowed_tools=["search.web", "calculator.compute"]
        ),
        "writer": AgentConfig(
            name="Writer",
            description="Content creation and editing",
            model="llama3.1:8b",
            temperature=0.7,
            allowed_tools=["file.read", "file.write"]
        ),
        "social": AgentConfig(
            name="Social",
            description="Social media content creation",
            model="llama3.1:8b",
            temperature=0.8
        )
    }
    
    for agent_id, config in agents_config.items():
        agent_registry.register_config(agent_id, config)
        agent_class = agent_registry._agent_classes.get(agent_id)
        if agent_class:
            agent = agent_class(
                agent_id=agent_id,
                config=config,
                model_provider=provider
            )
            agent_registry.register_agent(agent_id, agent)
            logger.info(f"Registered agent: {agent_id}")
    
    # Initialize tool registry
    tool_registry = get_tool_registry()
    
    # Register tools
    tools = [
        CalculatorTool(),
        SearchTool(),
        FileReadTool(),
        FileWriteTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)
        logger.info(f"Registered tool: {tool.tool_id}")
    
    # Initialize orchestration engine with orchestrator agent
    orchestrator = agent_registry.get_agent("orchestrator")
    if orchestrator:
        await get_orchestration_engine(orchestrator_agent=orchestrator)
        logger.info("Orchestration engine initialized")
    
    logger.info("Registries initialized successfully")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
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
    app.include_router(models.router, prefix="/api/v1", tags=["Models"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(tools.router, prefix="/api/v1/tools", tags=["Tools"])
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize on startup."""
        logger.info("Starting up OMNI API")
        await initialize_registries()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Shutting down OMNI API")
        if _model_provider:
            await _model_provider.close()
    
    logger.info("FastAPI application created")
    
    return app


# Create application instance
app = create_app()
