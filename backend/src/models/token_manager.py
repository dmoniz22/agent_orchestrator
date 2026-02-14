"""Token manager for handling context window limits."""

from typing import Any

from pydantic import BaseModel

from ..core.logging import get_logger
from .schemas import ModelInfo

logger = get_logger(__name__)


class TokenManager:
    """Manages token counting and context window truncation.
    
    Uses character-based heuristics for token estimation,
    with support for different model context windows.
    """
    
    # Characters per token approximation for different model families
    CHARS_PER_TOKEN = {
        "default": 4,
        "gpt": 4,
        "llama": 3.5,
        "qwen": 3.5,
        "mistral": 3.5,
    }
    
    # Safety margin to account for tokenization differences
    # Use a percentage-based margin for better scaling with small windows
    SAFETY_MARGIN = 20
    
    def __init__(self, chars_per_token: int = 4) -> None:
        """Initialize token manager.
        
        Args:
            chars_per_token: Average characters per token.
        """
        self.chars_per_token = chars_per_token
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Uses a simple character-based heuristic:
        tokens ≈ characters / chars_per_token
        
        Args:
            text: Text to estimate.
            
        Returns:
            Estimated token count.
        """
        return len(text) // self.chars_per_token
    
    def estimate_messages_tokens(
        self,
        messages: list[dict[str, Any]]
    ) -> int:
        """Estimate tokens for a list of messages.
        
        Args:
            messages: List of message dictionaries.
            
        Returns:
            Estimated total token count.
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if content:
                total += self.estimate_tokens(content)
            # Add overhead for message structure
            total += 4  # role tokens
        return total
    
    def truncate_messages(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
        preserve_system: bool = True
    ) -> list[dict[str, Any]]:
        """Truncate messages to fit within context window.
        
        Preserves system messages and most recent messages,
        removes older messages first.
        
        Args:
            messages: List of messages to truncate.
            max_tokens: Maximum allowed tokens.
            preserve_system: Whether to always keep system messages.
            
        Returns:
            Truncated message list.
        """
        if not messages:
            return []
        
        # Calculate available tokens (ensure we have at least some room)
        available_tokens = max(max_tokens - self.SAFETY_MARGIN, int(max_tokens * 0.5))
        
        # Separate system and non-system messages
        system_messages = []
        other_messages = []
        
        for msg in messages:
            if msg.get("role") == "system" and preserve_system:
                system_messages.append(msg)
            else:
                other_messages.append(msg)
        
        # Calculate system message tokens
        system_tokens = self.estimate_messages_tokens(system_messages)
        
        # Tokens available for non-system messages
        remaining_tokens = available_tokens - system_tokens
        
        if remaining_tokens <= 0 and system_tokens > 0:
            logger.warning(
                "System messages exceed context window",
                system_tokens=system_tokens,
                max_tokens=max_tokens
            )
            # Return just system messages truncated
            return self._truncate_to_token_limit(
                system_messages,
                available_tokens
            )
        
        # Keep most recent messages that fit
        selected_messages = []
        current_tokens = 0
        
        # Iterate from newest to oldest
        for msg in reversed(other_messages):
            msg_tokens = self.estimate_tokens(msg.get("content", "")) + 4
            
            if current_tokens + msg_tokens <= remaining_tokens:
                selected_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        result = system_messages + selected_messages
        
        if len(result) < len(messages):
            logger.info(
                "Truncated messages to fit context window",
                original_count=len(messages),
                truncated_count=len(result),
                original_tokens=self.estimate_messages_tokens(messages),
                final_tokens=self.estimate_messages_tokens(result),
                max_tokens=max_tokens
            )
        
        return result
    
    def _truncate_to_token_limit(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int
    ) -> list[dict[str, Any]]:
        """Truncate messages by removing content from oldest first.
        
        Args:
            messages: Messages to truncate.
            max_tokens: Maximum tokens allowed.
            
        Returns:
            Truncated messages.
        """
        result = []
        current_tokens = 0
        
        for msg in messages:
            content = msg.get("content", "")
            msg_tokens = self.estimate_tokens(content) + 4
            
            if current_tokens + msg_tokens <= max_tokens:
                result.append(msg)
                current_tokens += msg_tokens
            else:
                # Try to include partial content
                remaining = max_tokens - current_tokens - 4
                if remaining > 50:  # Only include if substantial
                    truncated_content = content[:remaining * self.chars_per_token]
                    result.append({
                        **msg,
                        "content": truncated_content + "... [truncated]"
                    })
                break
        
        return result
    
    def get_model_for_agent(
        self,
        agent_type: str,
        available_models: list[ModelInfo]
    ) -> ModelInfo:
        """Select appropriate model for agent type.
        
        Args:
            agent_type: Type of agent.
            available_models: List of available models.
            
        Returns:
            Selected model info.
        """
        # Model selection rules based on agent type
        preferences = {
            "orchestrator": ["llama3.1", "qwen2.5"],
            "coder": ["qwen2.5-coder", "codellama", "llama3.1"],
            "researcher": ["llama3.1", "mistral", "qwen2.5"],
            "writer": ["llama3.1", "mistral", "qwen2.5"],
            "social": ["llama3.1", "mistral"],
        }
        
        preferred = preferences.get(agent_type, ["llama3.1"])
        
        # Find first matching model
        for prefix in preferred:
            for model in available_models:
                if model.name.startswith(prefix):
                    return model
        
        # Fall back to first available
        if available_models:
            return available_models[0]
        
        # Default fallback
        return ModelInfo(name="llama3.1:8b", context_window=8192)


class ContextWindowManager:
    """Manages context window assembly from multiple sources."""
    
    def __init__(self, token_manager: TokenManager) -> None:
        """Initialize context window manager.
        
        Args:
            token_manager: Token manager instance.
        """
        self.token_manager = token_manager
    
    def build_context(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, Any]],
        retrieved_memories: list[str],
        tool_descriptions: list[str],
        max_tokens: int
    ) -> list[dict[str, Any]]:
        """Build complete context window with all components.
        
        Priority order:
        1. System prompt (highest priority)
        2. Recent conversation history
        3. Retrieved memories
        4. Tool descriptions (lowest priority)
        
        Args:
            system_prompt: System instruction prompt.
            conversation_history: Recent conversation messages.
            retrieved_memories: Retrieved long-term memories.
            tool_descriptions: Available tool descriptions.
            max_tokens: Maximum context window size.
            
        Returns:
            Assembled context messages.
        """
        # Start with system prompt
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add retrieved memories as context
        if retrieved_memories:
            memory_content = "Relevant context from previous conversations:\n" + "\n".join(
                f"- {mem}" for mem in retrieved_memories[:5]  # Limit to top 5
            )
            messages.append({"role": "system", "content": memory_content})
        
        # Add tool descriptions
        if tool_descriptions:
            tools_content = "Available tools:\n" + "\n".join(tool_descriptions)
            messages.append({"role": "system", "content": tools_content})
        
        # Truncate to fit
        return self.token_manager.truncate_messages(messages, max_tokens)