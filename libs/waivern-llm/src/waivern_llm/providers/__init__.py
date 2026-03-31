"""LLM Providers.

This package contains the LLMProvider protocol and concrete implementations
for different LLM providers (Anthropic, OpenAI, Google).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from waivern_llm.providers.anthropic import AnthropicProvider
from waivern_llm.providers.google import GoogleProvider
from waivern_llm.providers.openai import OpenAIProvider
from waivern_llm.providers.protocol import BatchLLMProvider, LLMProvider

if TYPE_CHECKING:
    from waivern_llm.di.configuration import LLMServiceConfiguration

__all__ = [
    "LLMProvider",
    "BatchLLMProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GoogleProvider",
    "create_provider",
]


def create_provider(config: LLMServiceConfiguration) -> LLMProvider:
    """Create the appropriate LLM provider based on configuration.

    Args:
        config: Validated LLM service configuration.

    Returns:
        LLMProvider instance for the configured provider.

    """
    match config.provider:
        case "anthropic":
            return AnthropicProvider(api_key=config.api_key, model=config.model)
        case "openai":
            return OpenAIProvider(
                api_key=config.api_key, model=config.model, base_url=config.base_url
            )
        case "google":
            return GoogleProvider(api_key=config.api_key, model=config.model)
        case _:
            # LLMServiceConfiguration validates provider, so this is unreachable
            msg = f"Unsupported provider: {config.provider}"
            raise ValueError(msg)
