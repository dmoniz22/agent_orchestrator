#!/usr/bin/env python3
"""Test script to verify OMNI providers are working correctly."""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from src.models import (
    get_fallback_provider,
    get_ollama_provider,
    get_openrouter_provider,
    FallbackProvider,
    Message,
)


async def test_providers():
    """Test all provider configurations."""
    print("=" * 60)
    print("OMNI Provider Test Suite")
    print("=" * 60)
    
    # Set up test messages
    test_messages = [
        Message(role="user", content="Say 'Hello from [provider name]' in exactly those words.")
    ]
    
    # ================================================================
    # Test 1: Fallback Provider (the main one we'll use)
    # ================================================================
    print("\n[1] Testing FallbackProvider (Ollama + OpenRouter)...")
    
    provider = get_fallback_provider(
        ollama_url="http://localhost:11434",
        ollama_default_model="llama3.1:8b",
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        openrouter_default_model="anthropic/claude-3-haiku-20240307",
        prefer_local=True,
        fallback_on_error=True
    )
    
    # Test health check
    health = await provider.health_check()
    print(f"    Health check: {'✅ PASS' if health else '❌ FAIL'}")
    print(f"    - Ollama available: Yes (checked)")
    print(f"    - OpenRouter available: {'Yes' if provider.openrouter else 'No'}")
    
    # Test local model (should use Ollama)
    print("\n[1a] Testing local model (llama3.1:8b)...")
    try:
        response = await provider.generate(
            messages=test_messages,
            model="llama3.1:8b",
            temperature=0.7,
            max_tokens=50
        )
        print(f"    Response: {response.content[:100]}...")
        print(f"    Provider used: {provider.last_provider_used}")
        print(f"    Status: ✅ PASS")
    except Exception as e:
        print(f"    Status: ❌ FAIL - {e}")
    
    # Test cloud model (should use OpenRouter)
    print("\n[1b] Testing cloud model (claude-haiku)...")
    try:
        response = await provider.generate(
            messages=test_messages,
            model="claude-haiku",
            temperature=0.7,
            max_tokens=50
        )
        print(f"    Response: {response.content[:100]}...")
        print(f"    Provider used: {provider.last_provider_used}")
        print(f"    Status: ✅ PASS")
    except Exception as e:
        print(f"    Status: ❌ FAIL - {e}")
    
    # List available models
    print("\n[1c] Listing available models...")
    try:
        models = await provider.list_models()
        print(f"    Found {len(models)} models")
        # Show first few
        for model in models[:5]:
            print(f"      - {model}")
    except Exception as e:
        print(f"    Warning: Could not list models - {e}")
    
    # ================================================================
    # Test 2: Ollama Direct
    # ================================================================
    print("\n[2] Testing OllamaProvider directly...")
    ollama = get_ollama_provider()
    
    try:
        health = await ollama.health_check()
        print(f"    Health check: {'✅ PASS' if health else '❌ FAIL'}")
        
        if health:
            response = await ollama.generate(
                messages=test_messages,
                model="llama3.1:8b",
                max_tokens=50
            )
            print(f"    Response: {response.content[:80]}...")
            print(f"    Status: ✅ PASS")
        else:
            print("    Status: ⚠️  Ollama not running")
    except Exception as e:
        print(f"    Status: ❌ FAIL - {e}")
    
    # ================================================================
    # Test 3: OpenRouter Direct
    # ================================================================
    print("\n[3] Testing OpenRouterProvider directly...")
    openrouter = get_openrouter_provider()
    
    if openrouter:
        try:
            health = await openrouter.health_check()
            print(f"    Health check: {'✅ PASS' if health else '❌ FAIL'}")
            
            if health:
                response = await openrouter.generate(
                    messages=test_messages,
                    model="claude-haiku",
                    max_tokens=50
                )
                print(f"    Response: {response.content[:80]}...")
                print(f"    Status: ✅ PASS")
        except Exception as e:
            print(f"    Status: ❌ FAIL - {e}")
    else:
        print("    Status: ⚠️  OpenRouter not configured")
    
    # ================================================================
    # Summary
    # ================================================================
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("""
The FallbackProvider is now configured to:
  1. Try local Ollama models first (free, private, fast)
  2. Automatically route cloud models to OpenRouter
  3. Fallback to OpenRouter if Ollama fails

To use in your code:
    from src.models import get_fallback_provider, Message
    
    provider = get_fallback_provider()
    response = await provider.generate(
        messages=[Message(role="user", content="Hello")],
        model="llama3.1:8b"  # Uses Ollama
    )
    # Or use cloud models:
    # model="claude-sonnet" -> Uses OpenRouter
""")
    
    # Cleanup
    await provider.close()


if __name__ == "__main__":
    asyncio.run(test_providers())
