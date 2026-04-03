"""System Info API endpoints."""

import platform
import sys
from datetime import datetime
from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/system/info")
async def get_system_info() -> dict[str, Any]:
    """Get system information.

    Returns:
        System information including Python version, platform, etc.
    """
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "start_time": datetime.now().isoformat(),
    }


@router.get("/system/status")
async def get_system_status() -> dict[str, Any]:
    """Get system status summary.

    Returns:
        System status including version and uptime info.
    """
    return {
        "version": "0.1.0",
        "environment": "production",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
    }
