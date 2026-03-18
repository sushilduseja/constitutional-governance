"""
OpenAI (GPT) adapter.
"""

from typing import Any

from sdk.adapters.base import LLMAdapter, LLMResponse


class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI GPT API (and Azure OpenAI)."""

    @property
    def provider_name(self) -> str:
        return "openai"

    def call(self, prompt: str, **kwargs) -> LLMResponse:
        from openai import OpenAI

        client = OpenAI()
        model = kwargs.get("model", "gpt-4o")

        raw = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1024),
        )

        return LLMResponse(
            raw=raw,
            text=self.extract_text(raw),
            model=self.get_model_id(raw),
            provider=self.provider_name,
        )

    def extract_text(self, raw_response: Any) -> str:
        if hasattr(raw_response, "choices") and raw_response.choices:
            return raw_response.choices[0].message.content or ""
        return str(raw_response)
