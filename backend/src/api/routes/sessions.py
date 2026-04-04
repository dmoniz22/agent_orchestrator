"""Session management endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class MessageResponse(BaseModel):
    """Message in history."""

    id: str
    role: str
    content: str
    timestamp: str | None


class SessionHistoryResponse(BaseModel):
    """Session history response."""

    session_id: str
    messages: list[MessageResponse]


@router.get("/{session_id}/history")
async def get_session_history(session_id: str) -> SessionHistoryResponse:
    """Get conversation history for a session.

    Args:
        session_id: Session identifier.

    Returns:
        Number of entries cleared.
    """
    # Create deterministic UUID from string session ID
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        import hashlib

        namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        hash_input = namespace.bytes + session_id.encode("utf-8")
        session_uuid = UUID(bytes=hashlib.md5(hash_input).digest())

    # Import inside function to avoid circular import
    from src.api.app import get_memory_manager

    memory_manager = get_memory_manager()

    try:
        entries = await memory_manager.get_conversation_history(session_id=session_uuid, limit=50)

        messages = []
        for entry in entries:
            messages.append(
                {
                    "id": str(entry.memory_id),
                    "role": entry.metadata.get("role", "assistant"),
                    "content": entry.content,
                    "timestamp": entry.created_at.isoformat() if entry.created_at else None,
                }
            )

        logger.info("Retrieved session history", session_id=session_id, message_count=len(messages))

        return {"session_id": session_id, "messages": messages}

    except Exception as e:
        logger.error("Failed to get session history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session history: {str(e)}",
        )


@router.delete("/{session_id}/history")
async def clear_session_history(session_id: str) -> dict:
    """Clear conversation history for a session.

    Args:
        session_id: Session identifier.

    Returns:
        Number of entries cleared.
    """
    try:
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            import hashlib

            namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
            hash_input = namespace.bytes + session_id.encode("utf-8")
            session_uuid = UUID(bytes=hashlib.md5(hash_input).digest())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid session ID format: {str(e)}"
        )

    memory_manager = get_memory_manager()

    try:
        result = await memory_manager.clear_session(session_uuid)

        logger.info(
            "Cleared session history",
            session_id=session_id,
            short_term=result.get("short_term", 0),
            long_term=result.get("long_term", 0),
        )

        return {"session_id": session_id, "cleared": result}

    except Exception as e:
        logger.error("Failed to clear session history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear session history: {str(e)}",
        )
