"""
LLMAdapter protocol.

Each LLM provider implements this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    raw: Any
    text: str
    model: str
    provider: str


class LLMAdapter(ABC):
    """Protocol for LLM providers. Implement this for each provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier: 'anthropic', 'openai', etc."""
        pass

    @abstractmethod
    def call(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Call the LLM with a text prompt.

        Args:
            prompt: The text prompt to send
            **kwargs: Provider-specific arguments (model, temperature, etc.)

        Returns:
            LLMResponse with the raw response, extracted text, model, and provider
        """
        pass

    @abstractmethod
    def extract_text(self, raw_response: Any) -> str:
        """
        Extract plain text from a provider-specific raw response.

        Different providers have different response structures:
        - Anthropic: response.content[0].text
        - OpenAI: response.choices[0].message.content
        - Etc.

        Args:
            raw_response: The raw response object from the LLM call

        Returns:
            Plain text string
        """
        pass

    def get_model_id(self, raw_response: Any) -> str:
        """
        Extract the model identifier from a response.

        Override if the provider uses a non-standard field.

        Args:
            raw_response: The raw response object

        Returns:
            Model identifier string
        """
        return getattr(raw_response, "model", "unknown")
