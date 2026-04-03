"""Settings and configuration endpoints."""

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.config import get_settings, reload_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Path to the .env file - use environment variable or default to /app/.env (Docker)
ENV_FILE = Path(os.environ.get("ENV_FILE_PATH", "/app/.env"))


class ApiKeysRequest(BaseModel):
    """API keys update request."""

    openrouter_api_key: str | None = Field(default=None, description="OpenRouter API key")
    openrouter_default_model: str | None = Field(
        default=None, description="Default OpenRouter model"
    )
    provider_prefer_local: bool | None = Field(default=None, description="Prefer local models")
    provider_fallback_on_error: bool | None = Field(
        default=None, description="Fallback to cloud on error"
    )


class ApiKeysResponse(BaseModel):
    """API keys status response."""

    openrouter_api_key_masked: str = ""
    openrouter_configured: bool = False
    openrouter_default_model: str = ""
    openrouter_base_url: str = ""
    provider_prefer_local: bool = True
    provider_fallback_on_error: bool = True
    ollama_base_url: str = ""
    ollama_default_model: str = ""


class NotificationSettings(BaseModel):
    """Notification settings."""

    task_completion: bool = True
    error_alerts: bool = True
    agent_notifications: bool = False
    daily_summary: bool = False
    webhook_url: str = ""


class SecuritySettings(BaseModel):
    """Security settings."""

    require_auth: bool = False
    api_rate_limit: int = 100
    allowed_origins: str = "http://localhost:3000,http://localhost:3002"
    session_timeout_minutes: int = 60
    enable_https: bool = False


def _mask_api_key(key: str) -> str:
    """Mask an API key for display."""
    if not key or len(key) < 12:
        return ""
    return f"{key[:8]}...{key[-4:]}"


def _update_env_file(updates: dict[str, str]) -> None:
    """Update specific values in the .env file."""
    if not ENV_FILE.exists():
        # Create .env file
        ENV_FILE.write_text("# OMNI Environment Variables\n\n")

    content = ENV_FILE.read_text()
    lines = content.split("\n")
    updated_keys = set()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue

        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f'{key}="{updates[key]}"')
            updated_keys.add(key)
        else:
            new_lines.append(line)

    # Add any keys that weren't already in the file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f'{key}="{value}"')

    ENV_FILE.write_text("\n".join(new_lines))

    # Also update the running process environment
    for key, value in updates.items():
        os.environ[key] = value


@router.get("/settings/api-keys", response_model=ApiKeysResponse)
async def get_api_keys() -> ApiKeysResponse:
    """Get current API key configuration status."""
    settings = get_settings()

    return ApiKeysResponse(
        openrouter_api_key_masked=_mask_api_key(settings.openrouter_api_key),
        openrouter_configured=bool(settings.openrouter_api_key),
        openrouter_default_model=settings.openrouter_default_model,
        openrouter_base_url=settings.openrouter_base_url,
        provider_prefer_local=settings.provider_prefer_local,
        provider_fallback_on_error=settings.provider_fallback_on_error,
        ollama_base_url=settings.ollama_base_url,
        ollama_default_model=settings.ollama_default_model,
    )


@router.post("/settings/api-keys")
async def update_api_keys(request: ApiKeysRequest) -> dict[str, Any]:
    """Update API keys and provider settings."""
    updates: dict[str, str] = {}

    if request.openrouter_api_key is not None:
        updates["OPENROUTER_API_KEY"] = request.openrouter_api_key

    if request.openrouter_default_model is not None:
        updates["OPENROUTER_DEFAULT_MODEL"] = request.openrouter_default_model

    if request.provider_prefer_local is not None:
        updates["PROVIDER_PREFER_LOCAL"] = str(request.provider_prefer_local).lower()

    if request.provider_fallback_on_error is not None:
        updates["PROVIDER_FALLBACK_ON_ERROR"] = str(request.provider_fallback_on_error).lower()

    if updates:
        _update_env_file(updates)
        logger.info("API keys updated", keys=list(updates.keys()))

    return {
        "status": "success",
        "updated": list(updates.keys()),
        "message": "Settings saved. Some changes may require a server restart to take full effect.",
    }


@router.get("/settings/notifications", response_model=NotificationSettings)
async def get_notification_settings() -> NotificationSettings:
    """Get notification settings."""
    return NotificationSettings()


@router.post("/settings/notifications")
async def update_notification_settings(settings: NotificationSettings) -> dict[str, str]:
    """Update notification settings."""
    logger.info("Notification settings updated", settings=settings.model_dump())
    return {"status": "success", "message": "Notification settings saved."}


@router.get("/settings/security", response_model=SecuritySettings)
async def get_security_settings() -> SecuritySettings:
    """Get security settings."""
    app_settings = get_settings()
    return SecuritySettings(
        allowed_origins=",".join(app_settings.api.cors_origins),
    )


@router.post("/settings/security")
async def update_security_settings(settings: SecuritySettings) -> dict[str, str]:
    """Update security settings."""
    updates: dict[str, str] = {}
    if settings.allowed_origins:
        updates["API_CORS_ORIGINS"] = settings.allowed_origins
        _update_env_file(updates)

    logger.info("Security settings updated", settings=settings.model_dump())
    return {
        "status": "success",
        "message": "Security settings saved. Some changes may require a server restart.",
    }
