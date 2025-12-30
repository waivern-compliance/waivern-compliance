"""Base configuration classes for services and components.

This module provides base configuration classes that all service and component
configurations should inherit from. It provides consistent validation,
immutability, and factory patterns across the framework.
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


class BaseComponentConfiguration(BaseModel):
    """Base class for all component configurations (analysers and connectors).

    This provides a consistent foundation for component configuration objects
    across the framework. All component configurations (PersonalDataAnalyserConfig,
    MySQLConnectorConfig, etc.) should inherit from this base class.

    Features:
        - Pydantic validation for type safety
        - Immutable by default (frozen) for configuration integrity
        - from_properties() factory method for dictionary-based creation
        - Strict validation (no extra fields allowed)

    Components vs Services:
        - Components: Transient instances created per execution (analysers, connectors)
        - Services: Singleton instances managed by DI container (LLM, database, cache)

    Example:
        ```python
        class PersonalDataAnalyserConfig(BaseComponentConfiguration):
            pattern_matching: PatternMatchingConfig
            llm_validation: LLMValidationConfig

        # Create from properties dictionary (from runbook)
        config = PersonalDataAnalyserConfig.from_properties({
            "pattern_matching": {"ruleset": "local/personal_data/1.0.0"},
            "llm_validation": {"enable_llm_validation": True}
        })

        # Or direct instantiation
        config = PersonalDataAnalyserConfig(
            pattern_matching=PatternMatchingConfig(ruleset="local/personal_data/1.0.0"),
            llm_validation=LLMValidationConfig(enable_llm_validation=True)
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
        objects from properties dictionaries (typically from runbook YAML properties).

        Subclasses should override this method to add environment variable
        support, defaults, or other preprocessing logic specific to the component.

        Args:
            properties: Dictionary containing configuration properties from runbook

        Returns:
            Validated configuration instance

        Raises:
            ValidationError: If properties are invalid or missing required fields

        Example:
            ```python
            config = PersonalDataAnalyserConfig.from_properties({
                "pattern_matching": {"ruleset": "local/personal_data/1.0.0"},
                "llm_validation": {"enable_llm_validation": True}
            })
            ```

        """
        return cls.model_validate(properties)
