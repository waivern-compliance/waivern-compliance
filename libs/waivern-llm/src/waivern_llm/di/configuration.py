"""Configuration for LLM service with dependency injection support.

This module provides configuration classes for LLM services that integrate
with the waivern-core DI system. Configuration supports both explicit
instantiation and environment variable fallback.
"""

from __future__ import annotations

import os
from typing import Any, Self, override

from pydantic import Field, field_validator
from waivern_core.services import BaseServiceConfiguration


class LLMServiceConfiguration(BaseServiceConfiguration):
    """Configuration for LLM service with environment fallback.

    This configuration class supports dual-mode operation:
    1. Explicit configuration with typed fields
    2. Environment variable fallback for zero-config scenarios

    The configuration validates provider names and API keys at creation time,
    ensuring invalid configurations are caught early.

    Attributes:
        provider: LLM provider name (anthropic, openai, or google)
        api_key: API key for the selected provider
        model: Optional model name (uses provider-specific default if None)

    Example:
        ```python
        # Explicit configuration
        config = LLMServiceConfiguration(
            provider="anthropic",
            api_key="sk-..."
        )

        # From properties dict with env fallback
        config = LLMServiceConfiguration.from_properties({
            "provider": "anthropic",
            "api_key": "sk-..."
        })

        # Zero-config (reads from environment)
        config = LLMServiceConfiguration.from_properties({})
        ```

    """

    provider: str = Field(description="LLM provider: anthropic, openai, or google")
    api_key: str = Field(description="API key for the provider")
    model: str | None = Field(
        default=None, description="Model name (provider default if None)"
    )
    base_url: str | None = Field(
        default=None,
        description="Base URL for OpenAI-compatible APIs (e.g., local LLMs)",
    )
    batch_mode: bool = Field(
        default=False,
        description="Use batch API for LLM calls (async, lower cost)",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate that provider is one of the supported options.

        Args:
            v: Provider name to validate

        Returns:
            Lowercase provider name

        Raises:
            ValueError: If provider is not supported

        """
        allowed = {"anthropic", "openai", "google"}
        provider_lower = v.lower()
        if provider_lower not in allowed:
            raise ValueError(f"Provider must be one of {allowed}, got: {v}")
        return provider_lower

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that API key is not empty.

        Args:
            v: API key to validate

        Returns:
            Stripped API key

        Raises:
            ValueError: If API key is empty or whitespace

        """
        if not v or not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from properties with environment fallback.

        This method implements a layered configuration system:
        1. Explicit properties (highest priority)
        2. Environment variables (fallback)
        3. Defaults (lowest priority)

        Environment variables used:
        - LLM_PROVIDER: Provider name (default: "anthropic")
        - ANTHROPIC_API_KEY: API key for Anthropic
        - OPENAI_API_KEY: API key for OpenAI
        - GOOGLE_API_KEY: API key for Google
        - ANTHROPIC_MODEL: Model for Anthropic
        - OPENAI_MODEL: Model for OpenAI
        - GOOGLE_MODEL: Model for Google
        - WAIVERN_LLM_BATCH_MODE: Enable batch API ("true"/"1"/"yes")

        Args:
            properties: Configuration properties dictionary

        Returns:
            Validated configuration instance

        Raises:
            ValidationError: If configuration is invalid

        Example:
            ```python
            # Explicit properties override environment
            config = LLMServiceConfiguration.from_properties({
                "provider": "anthropic",
                "api_key": "sk-..."
            })

            # Environment fallback
            os.environ["LLM_PROVIDER"] = "openai"
            os.environ["OPENAI_API_KEY"] = "sk-..."
            config = LLMServiceConfiguration.from_properties({})
            ```

        """
        config_data = properties.copy()

        # Provider (env fallback)
        if "provider" not in config_data:
            config_data["provider"] = os.getenv("LLM_PROVIDER", "anthropic")

        provider = config_data["provider"].lower()

        # API key (provider-specific env var)
        if "api_key" not in config_data:
            env_key_map = {
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "google": "GOOGLE_API_KEY",
            }
            config_data["api_key"] = os.getenv(env_key_map.get(provider, ""), "")

        # Model (provider-specific env var, optional)
        if "model" not in config_data:
            env_model_map = {
                "anthropic": "ANTHROPIC_MODEL",
                "openai": "OPENAI_MODEL",
                "google": "GOOGLE_MODEL",
            }
            model_value = os.getenv(env_model_map.get(provider, ""))
            if model_value:
                config_data["model"] = model_value

        # Base URL (OpenAI only, for local LLMs)
        if "base_url" not in config_data and provider == "openai":
            base_url = os.getenv("OPENAI_BASE_URL")
            if base_url:
                config_data["base_url"] = base_url

        # Batch mode (truthy string → True)
        if "batch_mode" not in config_data:
            batch_env = os.getenv("WAIVERN_LLM_BATCH_MODE", "")
            config_data["batch_mode"] = batch_env.lower() in ("true", "1", "yes")

        return cls.model_validate(config_data)

    def get_default_model(self) -> str:
        """Get provider-specific default model name.

        Returns the default model for the configured provider. This is used
        when no explicit model is specified.

        Returns:
            Default model name for the provider

        Example:
            ```python
            config = LLMServiceConfiguration(
                provider="anthropic",
                api_key="sk-..."
            )
            model = config.get_default_model()  # "claude-sonnet-4-5-20250929"
            ```

        """
        defaults = {
            "anthropic": "claude-sonnet-4-5-20250929",
            "openai": "gpt-4",
            "google": "gemini-pro",
        }
        return self.model or defaults[self.provider]
