"""LLM service factory."""

from __future__ import annotations

import os

from waivern_llm.anthropic import AnthropicLLMService
from waivern_llm.base import BaseLLMService
from waivern_llm.errors import LLMConfigurationError
from waivern_llm.google import GoogleLLMService
from waivern_llm.model_capabilities import ModelCapabilities
from waivern_llm.openai import OpenAILLMService


class LLMServiceFactory:
    """Factory for creating LLM service instances."""

    @staticmethod
    def create_service(
        model_name: str | None = None,
        api_key: str | None = None,
        capabilities: ModelCapabilities | None = None,
    ) -> BaseLLMService:
        """Create an LLM service instance based on LLM_PROVIDER environment variable.

        This method automatically selects the appropriate LLM provider based on the
        LLM_PROVIDER environment variable. If not set, defaults to Anthropic.

        Args:
            model_name: Optional model name (uses provider-specific env var or default if not provided)
            api_key: Optional API key (uses provider-specific env var if not provided)
            capabilities: Optional model capabilities override. If None, auto-detected from model name.

        Returns:
            Configured LLM service instance (AnthropicLLMService or OpenAILLMService)

        Raises:
            LLMConfigurationError: If LLM_PROVIDER specifies an unsupported provider

        """
        provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

        if provider == "anthropic":
            return LLMServiceFactory.create_anthropic_service(
                model_name=model_name, api_key=api_key, capabilities=capabilities
            )
        elif provider == "openai":
            return LLMServiceFactory.create_openai_service(
                model_name=model_name, api_key=api_key, capabilities=capabilities
            )
        elif provider == "google":
            return LLMServiceFactory.create_google_service(
                model_name=model_name, api_key=api_key, capabilities=capabilities
            )
        else:
            raise LLMConfigurationError(
                f"Unsupported LLM provider: '{provider}'. "
                f"Supported providers: 'anthropic', 'openai', 'google'. "
                f"Set LLM_PROVIDER environment variable to one of the supported providers."
            )

    @staticmethod
    def create_anthropic_service(
        model_name: str | None = None,
        api_key: str | None = None,
        capabilities: ModelCapabilities | None = None,
    ) -> AnthropicLLMService:
        """Create an Anthropic LLM service instance.

        Args:
            model_name: The Anthropic model to use (uses ANTHROPIC_MODEL env var or default if not provided)
            api_key: Optional API key (uses ANTHROPIC_API_KEY env var if not provided)
            capabilities: Optional model capabilities override. If None, auto-detected from model name.

        Returns:
            Configured AnthropicLLMService instance

        """
        return AnthropicLLMService(
            model_name=model_name, api_key=api_key, capabilities=capabilities
        )

    @staticmethod
    def create_openai_service(
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        capabilities: ModelCapabilities | None = None,
    ) -> OpenAILLMService:
        """Create an OpenAI LLM service instance.

        Args:
            model_name: The OpenAI model to use (uses OPENAI_MODEL env var or default if not provided)
            api_key: Optional API key (uses OPENAI_API_KEY env var if not provided)
            base_url: Optional base URL for OpenAI-compatible APIs (e.g., local LLMs)
            capabilities: Optional model capabilities override. If None, auto-detected from model name.

        Returns:
            Configured OpenAILLMService instance

        """
        return OpenAILLMService(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            capabilities=capabilities,
        )

    @staticmethod
    def create_google_service(
        model_name: str | None = None,
        api_key: str | None = None,
        capabilities: ModelCapabilities | None = None,
    ) -> GoogleLLMService:
        """Create a Google LLM service instance.

        Args:
            model_name: The Google model to use (uses GOOGLE_MODEL env var or default if not provided)
            api_key: Optional API key (uses GOOGLE_API_KEY env var if not provided)
            capabilities: Optional model capabilities override. If None, auto-detected from model name.

        Returns:
            Configured GoogleLLMService instance

        """
        return GoogleLLMService(
            model_name=model_name, api_key=api_key, capabilities=capabilities
        )
