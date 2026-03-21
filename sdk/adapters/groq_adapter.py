"""
Groq adapter for Constitutional Governance.

Uses Groq's free tier LLM API (OpenAI-compatible).
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from sdk.adapters.base import LLMAdapter, LLMResponse

logger = logging.getLogger(__name__)

GROQ_API_KEY_ENV = "GROQ_API_KEY"

DEFAULT_MODELS = [
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
    "groq/compound-mini",
    "llama-3.1-8b-instant",
]

RETRY_DELAY_SECONDS = 2.0

_RETRYABLE_ERRORS = frozenset([
    "429", "rate limit", "rate_limit",
    "timeout", "timed out", "unavailable",
    "overloaded", "service unavailable", "model_not_found",
    "context_length",
])


def _ensure_env_loaded() -> None:
    """Load .env file from project root if not already in environment."""
    if os.environ.get(GROQ_API_KEY_ENV):
        return
    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).resolve().parent.parent.parent
        load_dotenv(project_root / ".env", override=False)
    except Exception:
        pass


class GroqAdapter(LLMAdapter):
    """Adapter for Groq API (free tier, OpenAI-compatible)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        models: Optional[list[str]] = None,
    ):
        _ensure_env_loaded()
        self._api_key = api_key or os.environ.get(GROQ_API_KEY_ENV)
        logger.debug(f"GroqAdapter init: api_key provided={bool(api_key)}, final_key={bool(self._api_key)}")
        if not self._api_key:
            logger.warning(f"GROQ_API_KEY not found. Set it in the .env file or pass api_key to GroqAdapter()")
        self._models = models or DEFAULT_MODELS

    @property
    def provider_name(self) -> str:
        return "groq"

    def _get_client(self):
        import groq
        return groq.Groq(api_key=self._api_key)

    def _is_retryable(self, error: Exception) -> bool:
        error_str = str(error).lower()
        error_type = type(error).__name__
        return any(pattern in error_str or pattern in error_type
                   for pattern in _RETRYABLE_ERRORS)

    def call(self, prompt: str, **kwargs) -> LLMResponse:
        import groq

        if not self._api_key:
            raise PermissionError(
                f"GROQ_API_KEY not set. Set the {GROQ_API_KEY_ENV} environment variable."
            )

        client = self._get_client()
        temperature = kwargs.get("temperature", 0.3)
        max_tokens = kwargs.get("max_tokens", 1024)

        last_error: Optional[Exception] = None

        for i, model in enumerate(self._models):
            try:
                logger.debug(f"GroqAdapter: calling model={model} (attempt {i + 1}/{len(self._models)})")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return LLMResponse(
                    raw=response,
                    text=self.extract_text(response),
                    model=self.get_model_id(response),
                    provider=self.provider_name,
                )

            except groq.RateLimitError as e:
                logger.warning(f"GroqAdapter: rate limited on model={model}, trying next")
                last_error = e
                if i < len(self._models) - 1:
                    time.sleep(RETRY_DELAY_SECONDS)
                    client = self._get_client()

            except groq.APIError as e:
                error_str = str(e).lower()
                if "model" in error_str and ("not found" in error_str or "unavailable" in error_str):
                    logger.warning(f"GroqAdapter: model {model} not available, trying next")
                    last_error = e
                elif "429" in error_str:
                    logger.warning(f"GroqAdapter: rate limited on model={model}, trying next")
                    last_error = e
                    if i < len(self._models) - 1:
                        time.sleep(RETRY_DELAY_SECONDS)
                        client = self._get_client()
                else:
                    logger.error(f"GroqAdapter: API error on model={model}: {e}")
                    last_error = e
                    break

            except Exception as e:
                error_str = str(e).lower()
                if self._is_retryable(e):
                    logger.warning(f"GroqAdapter: retryable error on model={model}: {e}")
                    last_error = e
                    if i < len(self._models) - 1:
                        time.sleep(RETRY_DELAY_SECONDS)
                        client = self._get_client()
                else:
                    logger.error(f"GroqAdapter: non-retryable error on model={model}: {e}")
                    last_error = e
                    break

        if last_error:
            raise last_error
        raise RuntimeError("GroqAdapter: all models failed, no error captured")

    def extract_text(self, raw_response: Any) -> str:
        if hasattr(raw_response, "choices") and raw_response.choices:
            return raw_response.choices[0].message.content or ""
        return str(raw_response)
