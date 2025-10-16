"""Multi-provider LLM abstraction for Waivern Compliance Framework."""

__version__ = "0.1.0"

from waivern_llm.anthropic import AnthropicLLMService
from waivern_llm.base import BaseLLMService
from waivern_llm.errors import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMServiceError,
)
from waivern_llm.factory import LLMServiceFactory
from waivern_llm.google import GoogleLLMService
from waivern_llm.openai import OpenAILLMService

__all__ = [
    # Version
    "__version__",
    # Base
    "BaseLLMService",
    # Errors
    "LLMServiceError",
    "LLMConfigurationError",
    "LLMConnectionError",
    # Factory
    "LLMServiceFactory",
    # Providers
    "AnthropicLLMService",
    "OpenAILLMService",
    "GoogleLLMService",
]
