"""Ollama provider implementation."""

import json
from typing import Any, AsyncIterator

import httpx

from ..core.exceptions import ModelUnavailableError, ProviderError
from ..core.logging import get_logger
from ..core.utils import async_retry_with_backoff, estimate_token_count
from .provider import Message, ModelProvider, ModelResponse, ToolSchema

logger = get_logger(__name__)


class OllamaProvider(ModelProvider):
    """Ollama model provider.
    
    Communicates with Ollama's HTTP API for LLM inference.
    Supports JSON mode for structured outputs.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.1:8b",
        fallback_model: str | None = None,
        max_retries: int = 3,
        base_delay: float = 2.0
    ) -> None:
        """Initialize Ollama provider.
        
        Args:
            base_url: Ollama API base URL.
            default_model: Default model to use.
            fallback_model: Fallback model if primary unavailable.
            max_retries: Maximum retries on failure.
            base_delay: Base delay for exponential backoff.
        """
        super().__init__("ollama", base_url)
        self.default_model = default_model
        self.fallback_model = fallback_model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=60.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    @async_retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        exceptions=(httpx.NetworkError, httpx.TimeoutException, httpx.HTTPStatusError)
    )
    async def generate(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolSchema] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        format: str | None = None
    ) -> ModelResponse:
        """Generate response from Ollama.
        
        Args:
            messages: Conversation messages.
            model: Model to use.
            tools: Optional tools for tool calling.
            tool_choice: Optional tool choice strategy.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens.
            format: Output format (e.g., "json").
            
        Returns:
            ModelResponse with generated content.
            
        Raises:
            ProviderError: If generation fails.
        """
        client = await self._get_client()
        
        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            ollama_msg: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                ollama_msg["name"] = msg.name
            ollama_messages.append(ollama_msg)
        
        # Build request payload
        payload: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        # Add format for JSON mode
        if format == "json":
            payload["format"] = "json"
        
        # Add tools if provided
        if tools:
            # Handle both ToolSchema objects and dicts
            tool_dicts = []
            for tool in tools:
                if hasattr(tool, 'model_dump'):
                    tool_dicts.append(tool.model_dump())
                else:
                    tool_dicts.append(tool)
            payload["tools"] = tool_dicts
        
        try:
            logger.debug(
                "Sending request to Ollama",
                model=model,
                message_count=len(messages),
                has_tools=tools is not None
            )
            
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            message = data.get("message", {})
            content = message.get("content", "")
            
            # Check for tool calls in content (Ollama may include them in content)
            tool_calls = None
            if content.strip().startswith("{") and tools:
                try:
                    parsed = json.loads(content)
                    if "tool_calls" in parsed:
                        tool_calls = parsed["tool_calls"]
                    elif any(key in parsed for key in ["agent_id", "tool_id", "action"]):
                        # This might be an orchestrator decision
                        pass
                except json.JSONDecodeError:
                    pass
            
            # Extract usage info
            usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": (
                    data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                )
            }
            
            return ModelResponse(
                content=content,
                role="assistant",
                tool_calls=tool_calls,
                model=model,
                usage=usage,
                finish_reason="stop"
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ModelUnavailableError(model, "ollama") from e
            logger.error(
                "Ollama HTTP error",
                status_code=e.response.status_code,
                error=str(e)
            )
            raise ProviderError(
                f"Ollama HTTP error: {e.response.status_code}",
                provider="ollama"
            ) from e
        except httpx.NetworkError as e:
            logger.error("Ollama network error", error=str(e))
            raise ProviderError(
                "Network connection to Ollama failed",
                provider="ollama"
            ) from e
        except Exception as e:
            logger.error("Ollama generation error", error=str(e))
            raise ProviderError(
                f"Ollama generation failed: {e}",
                provider="ollama"
            ) from e
    
    async def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """Stream response from Ollama.
        
        Args:
            messages: Conversation messages.
            model: Model to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens.
            
        Yields:
            Response content chunks.
        """
        client = await self._get_client()
        
        # Convert messages to Ollama format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            if chunk:
                                yield chunk
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error("Ollama streaming error", error=str(e))
            raise ProviderError(
                f"Ollama streaming failed: {e}",
                provider="ollama"
            ) from e
    
    async def list_models(self) -> list[str]:
        """List available models.
        
        Returns:
            List of model names.
        """
        client = await self._get_client()
        
        try:
            response = await client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            return [model["name"] for model in models]
            
        except Exception as e:
            logger.error("Failed to list Ollama models", error=str(e))
            return []
    
    async def health_check(self) -> bool:
        """Check if Ollama is available.
        
        Returns:
            True if Ollama is responding.
        """
        try:
            client = await self._get_client()
            response = await client.get("/", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def embed(
        self,
        text: str,
        model: str = "nomic-embed-text"
    ) -> list[float]:
        """Generate embeddings using Ollama.
        
        Args:
            text: Text to embed.
            model: Embedding model.
            
        Returns:
            Embedding vector.
        """
        client = await self._get_client()
        
        payload = {
            "model": model,
            "prompt": text
        }
        
        try:
            response = await client.post("/api/embeddings", json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data.get("embedding", [])
            
        except Exception as e:
            logger.error("Ollama embedding error", error=str(e))
            raise ProviderError(
                f"Failed to generate embeddings: {e}",
                provider="ollama"
            ) from e


class OllamaProviderFactory:
    """Factory for creating Ollama provider instances."""
    
    @staticmethod
    def create(config: dict[str, Any]) -> OllamaProvider:
        """Create Ollama provider from configuration.
        
        Args:
            config: Provider configuration dictionary.
            
        Returns:
            Configured OllamaProvider instance.
        """
        return OllamaProvider(
            base_url=config.get("base_url", "http://localhost:11434"),
            default_model=config.get("default_model", "llama3.1:8b"),
            fallback_model=config.get("fallback_model"),
            max_retries=config.get("retry", {}).get("max_retries", 3),
            base_delay=config.get("retry", {}).get("base_delay_seconds", 2.0)
        )