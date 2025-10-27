"""Base configuration for infrastructure services.

This module provides the BaseServiceConfiguration class that all service
configurations should inherit from. It provides consistent validation,
immutability, and factory patterns across all infrastructure services.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict


class BaseServiceConfiguration(BaseModel):
    """Base class for all infrastructure service configurations.

    This provides a consistent foundation for service configuration objects
    across the framework. All service configurations (LLM, database, cache, etc.)
    should inherit from this base class.

    Features:
        - Pydantic validation for type safety
        - Immutable by default (frozen) for configuration integrity
        - from_properties() factory method for dictionary-based creation
        - Strict validation (no extra fields allowed)

    Example:
        ```python
        class LLMServiceConfiguration(BaseServiceConfiguration):
            provider: str
            api_key: str
            model: str | None = None

        # Create from properties dictionary
        config = LLMServiceConfiguration.from_properties({
            "provider": "anthropic",
            "api_key": "sk-..."
        })

        # Or direct instantiation
        config = LLMServiceConfiguration(
            provider="anthropic",
            api_key="sk-..."
        )
        ```

    """

    model_config = ConfigDict(
        # Immutable - configuration cannot be modified after creation
        frozen=True,
        # Strict - extra fields not in the model are rejected
        extra="forbid",
        # Validate on assignment (if frozen is False in subclass)
        validate_assignment=True,
    )

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from properties dictionary with validation.

        This factory method provides a consistent way to create configuration
        objects from properties dictionaries (e.g., from runbook properties,
        environment variables, or JSON).

        Subclasses should override this method to add environment variable
        support and other preprocessing logic.

        Args:
            properties: Dictionary containing configuration properties

        Returns:
            Validated configuration instance

        Raises:
            ValidationError: If properties are invalid or missing required fields

        Example:
            ```python
            config = LLMServiceConfiguration.from_properties({
                "provider": "anthropic",
                "api_key": "sk-..."
            })
            ```

        """
        return cls.model_validate(properties)
