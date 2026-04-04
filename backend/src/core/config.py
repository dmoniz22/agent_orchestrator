"""Core configuration module for OMNI."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False,
    )

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    name: str = Field(default="omni", description="Database name")
    user: str = Field(default="omni", description="Database user")
    password: str = Field(default="", description="Database password", repr=False)

    @property
    def url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )


class APIConfig(BaseSettings):
    """API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        case_sensitive=False,
    )

    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, description="API server port")
    cors_origins: list[str] = Field(
        default=[
            "*",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ],
        description="Allowed CORS origins",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # System
    system_name: str = Field(default="OMNI", description="System name")
    log_level: str = Field(default="INFO", description="Log level")
    environment: str = Field(default="development", description="Environment")

    # Limits
    max_steps_per_task: int = Field(default=10, description="Maximum steps per task")
    default_timeout_seconds: int = Field(default=120, description="Default timeout in seconds")

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig = Field(default_factory=APIConfig)

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_default_model: str = Field(default="llama3.1:8b", description="Default Ollama model")

    # OpenRouter (Cloud Fallback)
    openrouter_api_key: str = Field(default="", description="OpenRouter API key", repr=False)
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", description="OpenRouter base URL"
    )
    openrouter_default_model: str = Field(
        default="anthropic/claude-3-haiku-20240307", description="Default OpenRouter model"
    )
    openrouter_fallback_model: str = Field(
        default="openai/gpt-3.5-turbo-0125", description="OpenRouter fallback model"
    )
    openrouter_site_url: str = Field(
        default="http://localhost:3000", description="Site URL for OpenRouter rankings"
    )
    openrouter_site_name: str = Field(
        default="OMNI Multi-Agent System", description="Site name for OpenRouter rankings"
    )

    # Provider Fallback Settings
    provider_prefer_local: bool = Field(
        default=True, description="Prefer local Ollama models when available"
    )
    provider_fallback_on_error: bool = Field(
        default=True, description="Automatically fallback to cloud on error"
    )

    # Security
    secret_key: str = Field(default="", description="Secret key for JWT", repr=False)

    # External Services
    github_token: str = Field(default="", description="GitHub token", repr=False)
    twitter_bearer_token: str = Field(default="", description="Twitter bearer token", repr=False)
    twitter_api_key: str = Field(default="", description="Twitter API key", repr=False)
    twitter_api_secret: str = Field(default="", description="Twitter API secret", repr=False)
    twitter_access_token: str = Field(default="", description="Twitter access token", repr=False)
    twitter_access_token_secret: str = Field(
        default="", description="Twitter access token secret", repr=False
    )
    linkedin_access_token: str = Field(default="", description="LinkedIn access token", repr=False)


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load YAML configuration file.

    Args:
        config_path: Path to the YAML file.

    Returns:
        Dictionary with configuration values.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the YAML is invalid.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}") from e


class ConfigLoader:
    """Configuration loader that combines YAML files and environment variables."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize the config loader.

        Args:
            config_dir: Directory containing YAML config files.
                       Defaults to CONFIG/ relative to project root.
        """
        if config_dir is None:
            # Find project root (where .env or pyproject.toml exists)
            current = Path.cwd()
            while current != current.parent:
                if (current / ".env").exists() or (current / "pyproject.toml").exists():
                    break
                current = current.parent

            config_dir = current / "CONFIG"

        self.config_dir = config_dir
        self._cache: dict[str, dict[str, Any]] = {}

    def load_system_config(self) -> dict[str, Any]:
        """Load the main system configuration."""
        return self._load_config("system.yaml")

    def load_models_config(self) -> dict[str, Any]:
        """Load the models configuration."""
        return self._load_config("models.yaml")

    def load_skills_config(self) -> dict[str, Any]:
        """Load the skills configuration."""
        return self._load_config("skills.yaml")

    def load_agent_config(self, agent_id: str) -> dict[str, Any]:
        """Load a specific agent configuration."""
        return self._load_config(f"agents/{agent_id}.yaml")

    def load_tool_config(self, tool_id: str) -> dict[str, Any]:
        """Load a specific tool configuration."""
        return self._load_config(f"tools/{tool_id}.yaml")

    def list_agents(self) -> list[str]:
        """List all available agent configurations."""
        agents_dir = self.config_dir / "agents"
        if not agents_dir.exists():
            return []

        return [f.stem for f in agents_dir.iterdir() if f.suffix == ".yaml" and f.is_file()]

    def list_tools(self) -> list[str]:
        """List all available tool configurations."""
        tools_dir = self.config_dir / "tools"
        if not tools_dir.exists():
            return []

        return [f.stem for f in tools_dir.iterdir() if f.suffix == ".yaml" and f.is_file()]

    def _load_config(self, relative_path: str) -> dict[str, Any]:
        """Load a configuration file with caching."""
        if relative_path not in self._cache:
            config_path = self.config_dir / relative_path
            self._cache[relative_path] = load_yaml_config(config_path)

        return self._cache[relative_path]

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._cache.clear()


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance.

    This is a singleton that loads settings from environment variables.

    Returns:
        Settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment variables.

    Returns:
        Fresh Settings instance.
    """
    global _settings
    _settings = Settings()
    return _settings
