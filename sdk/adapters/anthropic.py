"""
Anthropic (Claude) adapter.
"""

import logging
import os
from pathlib import Path
from typing import Any

from sdk.adapters.base import LLMAdapter, LLMResponse

logger = logging.getLogger(__name__)


def _ensure_env_loaded() -> None:
    """Load .env file from project root if not already in environment."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).resolve().parent.parent.parent
        load_dotenv(project_root / ".env", override=False)
    except Exception:
        pass


class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic Claude API."""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def call(self, prompt: str, **kwargs) -> LLMResponse:
        import anthropic

        _ensure_env_loaded()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise PermissionError(
                "ANTHROPIC_API_KEY not set. Add it to your .env file or set the environment variable."
            )

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
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
