"""Unit tests for the Ollama provider."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.exceptions import ModelUnavailableError, ProviderError
from src.models.ollama import OllamaProvider
from src.models.provider import Message


class TestOllamaProvider:
    """Test cases for OllamaProvider."""
    
    @pytest.fixture
    def provider(self):
        """Create Ollama provider instance."""
        return OllamaProvider(
            base_url="http://localhost:11434",
            default_model="llama3.1:8b",
            fallback_model="qwen2.5:7b"
        )
    
    @pytest.fixture
    def sample_messages(self):
        """Create sample messages."""
        return [
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="Hello"),
        ]
    
    @pytest.mark.asyncio
    async def test_generate_success(self, provider, sample_messages):
        """Test successful generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Hello! How can I help you?"},
            "model": "llama3.1:8b",
            "prompt_eval_count": 10,
            "eval_count": 5
        }
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            result = await provider.generate(
                messages=sample_messages,
                model="llama3.1:8b",
                temperature=0.7
            )
        
        assert result.content == "Hello! How can I help you?"
        assert result.model == "llama3.1:8b"
        assert result.finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_generate_with_json_format(self, provider, sample_messages):
        """Test generation with JSON format."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": '{"key": "value"}'},
            "model": "llama3.1:8b",
            "prompt_eval_count": 10,
            "eval_count": 5
        }
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            result = await provider.generate(
                messages=sample_messages,
                model="llama3.1:8b",
                format="json"
            )
        
        assert result.content == '{"key": "value"}'
    
    @pytest.mark.asyncio
    async def test_generate_with_tools(self, provider, sample_messages):
        """Test generation with tool calling."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": '{"tool_calls": [{"name": "search", "args": {}}]}'},
            "model": "llama3.1:8b",
            "prompt_eval_count": 10,
            "eval_count": 10
        }
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        
        tools = [{"type": "function", "function": {"name": "search"}}]
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            result = await provider.generate(
                messages=sample_messages,
                model="llama3.1:8b",
                tools=tools
            )
        
        assert result.tool_calls is not None
    
    @pytest.mark.asyncio
    async def test_generate_model_unavailable(self, provider, sample_messages):
        """Test handling of 404 model unavailable error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        
        http_error = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response
        )
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=http_error)
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            with pytest.raises(ModelUnavailableError) as exc_info:
                await provider.generate(
                    messages=sample_messages,
                    model="nonexistent-model"
                )
        
        assert "nonexistent-model" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_network_error(self, provider, sample_messages):
        """Test handling of network errors."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.NetworkError("Connection refused"))
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            with pytest.raises(ProviderError) as exc_info:
                await provider.generate(
                    messages=sample_messages,
                    model="llama3.1:8b"
                )
        
        assert "network" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_list_models(self, provider):
        """Test listing available models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.1:8b"},
                {"name": "qwen2.5:7b"},
                {"name": "nomic-embed-text"}
            ]
        }
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            models = await provider.list_models()
        
        assert "llama3.1:8b" in models
        assert "qwen2.5:7b" in models
        assert "nomic-embed-text" in models
    
    @pytest.mark.asyncio
    async def test_list_models_error(self, provider):
        """Test error handling when listing models."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.NetworkError("Failed"))
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            models = await provider.list_models()
        
        # Should return empty list on error
        assert models == []
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test health check when Ollama is available."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            is_healthy = await provider.health_check()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider):
        """Test health check when Ollama is unavailable."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.NetworkError("Failed"))
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            is_healthy = await provider.health_check()
        
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_embed(self, provider):
        """Test embedding generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5] * 300  # 1500 dimensions
        }
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            embedding = await provider.embed("Test text", model="nomic-embed-text")
        
        assert len(embedding) == 1500
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self):
        """Test provider initialization."""
        provider = OllamaProvider(
            base_url="http://ollama:11434",
            default_model="llama3.1:8b",
            fallback_model="qwen2.5:7b",
            max_retries=5,
            base_delay=1.0
        )
        
        assert provider.base_url == "http://ollama:11434"
        assert provider.default_model == "llama3.1:8b"
        assert provider.fallback_model == "qwen2.5:7b"
        assert provider.max_retries == 5
        assert provider.base_delay == 1.0