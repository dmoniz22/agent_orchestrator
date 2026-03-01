"""OpenRouter provider implementation with access to multiple model families."""
import json
from typing import Any, AsyncIterator

import httpx

from ..core.exceptions import ModelUnavailableError, ProviderError
from ..core.logging import get_logger
from ..core.utils import async_retry_with_backoff
from .provider import Message, ModelProvider, ModelResponse, ToolSchema

logger = get_logger(__name__)


class OpenRouterProvider(ModelProvider):
    """OpenRouter model provider.
    
    Provides access to 100+ models including:
    - Anthropic: claude-3-opus, claude-3-sonnet, claude-3-haiku
    - OpenAI: gpt-4o, gpt-4-turbo, gpt-3.5-turbo
    - Google: gemini-pro, gemini-flash
    - Meta: llama-3.1-70b, llama-3.1-8b
    - And many more via OpenRouter's unified API
    
    Docs: https://openrouter.ai/docs
    """
    
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Popular model aliases for convenience
    MODEL_ALIASES = {
        # Anthropic
        "claude-opus": "anthropic/claude-3-opus-20240229",
        "claude-sonnet": "anthropic/claude-3.5-sonnet-20241022",
        "claude-haiku": "anthropic/claude-3-haiku-20240307",
        # OpenAI
        "gpt-4o": "openai/gpt-4o-2024-08-01",
        "gpt-4o-mini": "openai/gpt-4o-mini-2024-07-18",
        "gpt-4-turbo": "openai/gpt-4-turbo-2024-04-09",
        "gpt-3.5": "openai/gpt-3.5-turbo-0125",
        # Google
        "gemini-pro": "google/gemini-pro-1.5",
        "gemini-flash": "google/gemini-flash-1.5-8b",
        # Meta
        "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
        "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct",
        "llama-3-70b": "meta-llama/llama-3-70b-instruct",
        "llama-3-8b": "meta-llama/llama-3-8b-instruct",
        # Mistral
        "mistral-large": "mistralai/mistral-large",
        "mistral-medium": "mistralai/mistral-medium-2312",
        "mistral-small": "mistralai/mistral-small-2409",
        # DeepSeek
        "deepseek-chat": "deepseek/deepseek-chat",
        "deepseek-coder": "deepseek/deepseek-coder",
        # Qwen
        "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct",
        "qwen-2.5-14b": "qwen/qwen-2.5-14b-instruct",
    }
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: str = "anthropic/claude-3-haiku-20240307",
        fallback_model: str | None = "openai/gpt-3.5-turbo-0125",
        max_retries: int = 3,
        base_delay: float = 2.0,
        site_url: str | None = None,
        site_name: str | None = None
    ) -> None:
        """Initialize OpenRouter provider."""
        super().__init__("openrouter", base_url)
        self.api_key = api_key
        self.default_model = default_model
        self.fallback_model = fallback_model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.site_url = site_url
        self.site_name = site_name
        self._client: httpx.AsyncClient | None = None
        
    def _resolve_model(self, model: str) -> str:
        """Resolve model alias to full OpenRouter model ID."""
        return self.MODEL_ALIASES.get(model, model)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=120.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _build_headers(self) -> dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.site_name:
            headers["X-Title"] = self.site_name
        return headers
    
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
        """Generate response from OpenRouter."""
        client = await self._get_client()
        resolved_model = self._resolve_model(model)
        
        # Convert messages to OpenAI format
        openrouter_messages = []
        for msg in messages:
            msg_dict: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            openrouter_messages.append(msg_dict)
        
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": openrouter_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if format == "json":
            payload["response_format"] = {"type": "json_object"}
        
        if tools:
            tool_dicts = [t.model_dump() if hasattr(t, 'model_dump') else t for t in tools]
            payload["tools"] = tool_dicts
            if tool_choice:
                payload["tool_choice"] = tool_choice
        
        try:
            logger.debug("Sending request to OpenRouter", model=resolved_model, message_count=len(messages))
            
            response = await client.post("/chat/completions", json=payload, headers=self._build_headers())
            response.raise_for_status()
            data = response.json()
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            
            # Handle tool calls
            tool_calls = None
            if message.get("tool_calls"):
                tool_calls = [tc.model_dump() if hasattr(tc, 'model_dump') else tc for tc in message["tool_calls"]]
            
            # Extract usage
            usage = data.get("usage", {})
            
            return ModelResponse(
                content=content,
                role="assistant",
                tool_calls=tool_calls,
                model=resolved_model,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                },
                finish_reason=choice.get("finish_reason", "stop")
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ProviderError("Invalid OpenRouter API key", provider="openrouter") from e
            if e.response.status_code == 404:
                raise ModelUnavailableError(model, "openrouter") from e
            logger.error("OpenRouter HTTP error", status_code=e.response.status_code, error=str(e))
            raise ProviderError(f"OpenRouter HTTP error: {e.response.status_code}", provider="openrouter") from e
        except httpx.NetworkError as e:
            logger.error("OpenRouter network error", error=str(e))
            raise ProviderError("Network connection to OpenRouter failed", provider="openrouter") from e
        except Exception as e:
            logger.error("OpenRouter generation error", error=str(e))
            raise ProviderError(f"OpenRouter generation failed: {e}", provider="openrouter") from e
    
    async def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """Stream response from OpenRouter."""
        client = await self._get_client()
        resolved_model = self._resolve_model(model)
        
        openrouter_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        payload = {
            "model": resolved_model,
            "messages": openrouter_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        try:
            async with client.stream("POST", "/chat/completions", json=payload, headers=self._build_headers()) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.strip() or line.startswith("data: "):
                        continue
                    
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if delta.get("content"):
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error("OpenRouter streaming error", error=str(e))
            raise ProviderError(f"OpenRouter streaming failed: {e}", provider="openrouter") from e
    
    async def list_models(self) -> list[str]:
        """List available models from OpenRouter."""
        client = await self._get_client()
        
        try:
            response = await client.get(
                "/models",
                headers=self._build_headers()
            )
            response.raise_for_status()
            data = response.json()
            
            models = data.get("data", [])
            return [m.get("id", "") for m in models if m.get("id")]
            
        except Exception as e:
            logger.error("Failed to list OpenRouter models", error=str(e))
            return list(self.MODEL_ALIASES.keys())
    
    async def health_check(self) -> bool:
        """Check if OpenRouter is available."""
        try:
            client = await self._get_client()
            response = await client.get("/models", headers=self._build_headers(), timeout=10.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def embed(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        """Generate embeddings using Ollama (through OpenRouter if available)."""
        # OpenRouter doesn't directly support embeddings, but we can route to compatible endpoints
        raise NotImplementedError("Embeddings via OpenRouter not yet supported")


class OpenRouterProviderFactory:
    """Factory for creating OpenRouter provider instances."""
    
    @staticmethod
    def create(config: dict[str, Any]) -> OpenRouterProvider:
        """Create OpenRouter provider from configuration."""
        return OpenRouterProvider(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://openrouter.ai/api/v1"),
            default_model=config.get("default_model", "anthropic/claude-3-haiku-20240307"),
            fallback_model=config.get("fallback_model"),
            max_retries=config.get("retry", {}).get("max_retries", 3),
            base_delay=config.get("retry", {}).get("base_delay_seconds", 2.0),
            site_url=config.get("site_url"),
            site_name=config.get("site_name")
        )
