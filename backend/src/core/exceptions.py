"""Core exception hierarchy for OMNI."""

from typing import Any


class OMNIError(Exception):
    """Base exception for all OMNI errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        """Initialize the error.
        
        Args:
            message: Human-readable error message.
            error_code: Machine-readable error code.
            details: Additional error context.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "error": {
                "message": self.message,
                "code": self.error_code,
                "details": self.details,
            }
        }


class ConfigError(OMNIError):
    """Error loading or validating configuration."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, error_code="CONFIG_ERROR", details=details)


class InvalidStateTransitionError(OMNIError):
    """Attempted an invalid state transition in the state machine."""
    
    def __init__(
        self,
        from_state: str,
        to_state: str,
        valid_transitions: list[str] | None = None
    ) -> None:
        message = f"Invalid state transition: {from_state} -> {to_state}"
        details = {"from_state": from_state, "to_state": to_state}
        if valid_transitions:
            details["valid_transitions"] = valid_transitions
        
        super().__init__(
            message,
            error_code="INVALID_STATE_TRANSITION",
            details=details
        )
        self.from_state = from_state
        self.to_state = to_state
        self.valid_transitions = valid_transitions or []


class ProviderError(OMNIError):
    """Error communicating with LLM provider."""
    
    def __init__(
        self,
        message: str,
        provider: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        error_details = details or {}
        if provider:
            error_details["provider"] = provider
        
        super().__init__(
            message,
            error_code="PROVIDER_ERROR",
            details=error_details
        )
        self.provider = provider


class ModelUnavailableError(ProviderError):
    """Requested model is not available."""
    
    def __init__(self, model: str, provider: str | None = None) -> None:
        message = f"Model '{model}' is not available"
        super().__init__(
            message,
            provider=provider,
            details={"model": model}
        )
        self.model = model


class AgentError(OMNIError):
    """Error in agent execution."""
    
    def __init__(
        self,
        message: str,
        agent_id: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        error_details = details or {}
        if agent_id:
            error_details["agent_id"] = agent_id
        
        super().__init__(
            message,
            error_code="AGENT_ERROR",
            details=error_details
        )
        self.agent_id = agent_id


class ToolExecutionError(OMNIError):
    """Error executing a tool/skill."""
    
    def __init__(
        self,
        message: str,
        tool_id: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        error_details = details or {}
        if tool_id:
            error_details["tool_id"] = tool_id
        
        super().__init__(
            message,
            error_code="TOOL_EXECUTION_ERROR",
            details=error_details
        )
        self.tool_id = tool_id


class ToolTimeoutError(ToolExecutionError):
    """Tool execution timed out."""
    
    def __init__(self, tool_id: str, timeout_seconds: int) -> None:
        message = f"Tool '{tool_id}' timed out after {timeout_seconds} seconds"
        super().__init__(
            message,
            tool_id=tool_id,
            details={"timeout_seconds": timeout_seconds}
        )
        self.timeout_seconds = timeout_seconds


class ToolAuthError(ToolExecutionError):
    """Tool authentication failed."""
    
    def __init__(self, tool_id: str, message: str | None = None) -> None:
        msg = message or f"Tool '{tool_id}' authentication failed"
        super().__init__(msg, tool_id=tool_id, details={"auth_failed": True})


class SandboxError(ToolExecutionError):
    """Error in sandbox execution."""
    
    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
        stderr: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        error_details = details or {}
        if exit_code is not None:
            error_details["exit_code"] = exit_code
        if stderr:
            error_details["stderr"] = stderr
        
        super().__init__(
            message,
            tool_id="sandbox",
            details=error_details
        )
        self.exit_code = exit_code
        self.stderr = stderr


class SafetyCheckError(ToolExecutionError):
    """Code failed safety check before sandbox execution."""
    
    def __init__(self, message: str, violations: list[str] | None = None) -> None:
        details = {"violations": violations or []}
        super().__init__(
            message,
            tool_id="safety_check",
            details=details
        )
        self.violations = violations or []


class DatabaseError(OMNIError):
    """Database operation error."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class MemoryError(OMNIError):
    """Memory system error."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, error_code="MEMORY_ERROR", details=details)


class OrchestrationError(OMNIError):
    """Orchestration engine error."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, error_code="ORCHESTRATION_ERROR", details=details)


class ValidationError(OMNIError):
    """Input validation error."""
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        error_details = details or {}
        if field:
            error_details["field"] = field
        
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            details=error_details
        )
        self.field = field


class RouterError(OMNIError):
    """Error dispatching or routing decisions."""
    
    def __init__(
        self,
        message: str,
        action: str | None = None,
        agent_id: str | None = None,
        tool_id: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        error_details = details or {}
        if action:
            error_details["action"] = action
        if agent_id:
            error_details["agent_id"] = agent_id
        if tool_id:
            error_details["tool_id"] = tool_id
        
        super().__init__(
            message,
            error_code="ROUTER_ERROR",
            details=error_details
        )
        self.action = action
        self.agent_id = agent_id
        self.tool_id = tool_id