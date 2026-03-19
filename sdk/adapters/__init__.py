"""
SDK adapters for different LLM providers.
"""

from sdk.adapters.base import LLMAdapter, LLMResponse
from sdk.adapters.anthropic import AnthropicAdapter
from sdk.adapters.groq_adapter import GroqAdapter
from sdk.adapters.openai import OpenAIAdapter

ADAPTERS = {
    "anthropic": AnthropicAdapter,
    "groq": GroqAdapter,
    "openai": OpenAIAdapter,
}


def get_adapter(provider: str) -> LLMAdapter:
    """Get the adapter for a given provider."""
    adapter_cls = ADAPTERS.get(provider.lower())
    if not adapter_cls:
        raise ValueError(f"Unknown provider: {provider}. Known: {list(ADAPTERS.keys())}")
    return adapter_cls()
