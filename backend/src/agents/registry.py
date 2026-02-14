"""Agent registry for managing agent lifecycle and discovery."""

from typing import Any
from pathlib import Path
import yaml

from src.core.exceptions import AgentError
from src.core.logging import get_logger
from src.agents.base import AgentConfig, BaseAgent

logger = get_logger(__name__)


class AgentRegistry:
    """Registry for managing agent instances and configurations.
    
    Handles:
    - Agent registration and discovery
    - Configuration loading from YAML files
    - Agent instance creation and caching
    """
    
    def __init__(self, config_dir: Path | str | None = None) -> None:
        """Initialize agent registry.
        
        Args:
            config_dir: Directory containing agent YAML configurations.
        """
        self._agents: dict[str, BaseAgent] = {}
        self._configs: dict[str, AgentConfig] = {}
        self._agent_classes: dict[str, type[BaseAgent]] = {}
        
        if config_dir:
            self.config_dir = Path(config_dir)
            self._load_configs_from_directory()
        else:
            self.config_dir = None
        
        logger.info(
            "AgentRegistry initialized",
            config_dir=str(self.config_dir) if self.config_dir else None
        )
    
    def register_agent_class(
        self,
        agent_type: str,
        agent_class: type[BaseAgent]
    ) -> None:
        """Register an agent class for instantiation.
        
        Args:
            agent_type: Type identifier for the agent.
            agent_class: Agent class to register.
        """
        self._agent_classes[agent_type] = agent_class
        logger.info(
            "Registered agent class",
            agent_type=agent_type,
            class_name=agent_class.__name__
        )
    
    def register_config(
        self,
        agent_id: str,
        config: AgentConfig
    ) -> None:
        """Register an agent configuration.
        
        Args:
            agent_id: Unique agent identifier.
            config: Agent configuration.
        """
        self._configs[agent_id] = config
        logger.info(
            "Registered agent config",
            agent_id=agent_id,
            name=config.name
        )
    
    def register_agent(
        self,
        agent_id: str,
        agent: BaseAgent
    ) -> None:
        """Register an agent instance.
        
        Args:
            agent_id: Unique agent identifier.
            agent: Agent instance.
        """
        self._agents[agent_id] = agent
        logger.info(
            "Registered agent instance",
            agent_id=agent_id,
            name=agent.config.name
        )
    
    def get_agent(self, agent_id: str) -> BaseAgent | None:
        """Get an agent instance by ID.
        
        Args:
            agent_id: Agent identifier.
            
        Returns:
            Agent instance or None if not found.
        """
        return self._agents.get(agent_id)
    
    def get_config(self, agent_id: str) -> AgentConfig | None:
        """Get an agent configuration by ID.
        
        Args:
            agent_id: Agent identifier.
            
        Returns:
            Agent configuration or None if not found.
        """
        return self._configs.get(agent_id)
    
    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents.
        
        Returns:
            List of agent information dictionaries.
        """
        return [
            {
                "agent_id": agent_id,
                **agent.get_info()
            }
            for agent_id, agent in self._agents.items()
        ]
    
    def list_configs(self) -> list[dict[str, Any]]:
        """List all registered configurations.
        
        Returns:
            List of configuration information dictionaries.
        """
        return [
            {
                "agent_id": agent_id,
                "name": config.name,
                "description": config.description,
                "model": config.model,
                "allowed_tools": config.allowed_tools
            }
            for agent_id, config in self._configs.items()
        ]
    
    def create_agent(
        self,
        agent_id: str,
        agent_type: str,
        model_provider=None,
        override_config: dict[str, Any] | None = None
    ) -> BaseAgent:
        """Create and register an agent instance.
        
        Args:
            agent_id: Unique agent identifier.
            agent_type: Type of agent to create.
            model_provider: Model provider for the agent.
            override_config: Optional config overrides.
            
        Returns:
            Created agent instance.
            
        Raises:
            AgentError: If agent type not registered or config missing.
        """
        # Get agent class
        if agent_type not in self._agent_classes:
            raise AgentError(
                message=f"Unknown agent type: {agent_type}",
                agent_id=agent_id
            )
        
        agent_class = self._agent_classes[agent_type]
        
        # Get or create config
        if agent_id in self._configs:
            base_config = self._configs[agent_id]
        else:
            # Use default config
            base_config = AgentConfig(
                name=agent_id,
                description=f"{agent_type} agent"
            )
        
        # Apply overrides
        if override_config:
            config_dict = base_config.model_dump()
            config_dict.update(override_config)
            base_config = AgentConfig(**config_dict)
        
        # Create agent instance
        agent = agent_class(
            agent_id=agent_id,
            config=base_config,
            model_provider=model_provider
        )
        
        # Register the instance
        self.register_agent(agent_id, agent)
        
        return agent
    
    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent and its config.
        
        Args:
            agent_id: Agent identifier.
            
        Returns:
            True if agent was found and removed.
        """
        found = False
        
        if agent_id in self._agents:
            del self._agents[agent_id]
            found = True
        
        if agent_id in self._configs:
            del self._configs[agent_id]
            found = True
        
        if found:
            logger.info("Unregistered agent", agent_id=agent_id)
        
        return found
    
    def _load_configs_from_directory(self) -> None:
        """Load agent configurations from YAML files."""
        if not self.config_dir or not self.config_dir.exists():
            logger.warning(
                "Config directory not found",
                config_dir=str(self.config_dir)
            )
            return
        
        yaml_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.yml"))
        
        for config_file in yaml_files:
            try:
                self._load_config_file(config_file)
            except Exception as e:
                logger.error(
                    "Failed to load config file",
                    file=str(config_file),
                    error=str(e)
                )
    
    def _load_config_file(self, config_file: Path) -> None:
        """Load a single config file.
        
        Args:
            config_file: Path to YAML config file.
        """
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            return
        
        # Support multiple agents per file or single agent
        if isinstance(data, list):
            configs = data
        elif isinstance(data, dict) and 'agents' in data:
            configs = data['agents']
        else:
            configs = [data]
        
        for config_data in configs:
            agent_id = config_data.get('agent_id') or config_file.stem
            
            try:
                config = AgentConfig(**config_data)
                self.register_config(agent_id, config)
            except Exception as e:
                logger.error(
                    "Failed to parse agent config",
                    agent_id=agent_id,
                    error=str(e)
                )


# Global registry instance
_registry: AgentRegistry | None = None


def get_agent_registry(
    config_dir: Path | str | None = None
) -> AgentRegistry:
    """Get or create global agent registry.
    
    Args:
        config_dir: Directory containing agent configurations.
        
    Returns:
        AgentRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = AgentRegistry(config_dir)
    return _registry