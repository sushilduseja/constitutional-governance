"""
OpenAI (GPT) adapter.
"""

import logging
import os
from pathlib import Path
from typing import Any

from sdk.adapters.base import LLMAdapter, LLMResponse

logger = logging.getLogger(__name__)


def _ensure_env_loaded() -> None:
    """Load .env file from project root if not already in environment."""
    if os.environ.get("OPENAI_API_KEY"):
        return
    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).resolve().parent.parent.parent
        load_dotenv(project_root / ".env", override=False)
    except Exception:
        pass


class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI GPT API (and Azure OpenAI)."""

    @property
    def provider_name(self) -> str:
        return "openai"

    def call(self, prompt: str, **kwargs) -> LLMResponse:
        from openai import OpenAI

        _ensure_env_loaded()
        if not os.environ.get("OPENAI_API_KEY"):
            raise PermissionError(
                "OPENAI_API_KEY not set. Add it to your .env file or set the environment variable."
            )

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
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
