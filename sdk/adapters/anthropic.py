"""
Anthropic (Claude) adapter.
"""

from typing import Any

from sdk.adapters.base import LLMAdapter, LLMResponse


class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic Claude API."""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def call(self, prompt: str, **kwargs) -> LLMResponse:
        import anthropic

        client = anthropic.Anthropic()
        model = kwargs.get("model", "claude-3-5-sonnet-20260220")

        raw = client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=[{"role": "user", "content": prompt}],
        )

        return LLMResponse(
            raw=raw,
            text=self.extract_text(raw),
            model=self.get_model_id(raw),
            provider=self.provider_name,
        )

    def extract_text(self, raw_response: Any) -> str:
        if hasattr(raw_response, "content") and raw_response.content:
            return raw_response.content[0].text
        return str(raw_response)
