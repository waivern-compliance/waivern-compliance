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

        Subclasses override this method to assemble the validated config from raw
        inputs — overlaying environment variables is one common case, but assembly
        also covers dispatching on a field (e.g. ``LLMServiceConfiguration`` loads
        provider-specific keys and models), layered fallbacks, and post-validation
        enrichment.

        ``from_properties`` is the untrusted-input boundary (runbook properties,
        environment variables): overriding subclasses translate validation failures
        into a ``ServiceConfigError``-family error (typically via ``validate_or_raise``)
        so callers get a uniform, structured config error rather than a raw
        ``ValidationError``. Direct construction with typed fields
        (``LLMServiceConfiguration(provider=..., api_key=...)``) is the internal path
        and surfaces Pydantic's raw ``ValidationError``. The base implementation here
        does not translate — a subclass relying on it gets the raw error.

        Args:
            properties: Dictionary containing configuration properties

        Returns:
            Validated configuration instance

        Raises:
            ValidationError: If properties are invalid (base implementation only;
                overriding subclasses raise their ``ServiceConfigError``-family error)

        Example:
            ```python
            config = LLMServiceConfiguration.from_properties({
                "provider": "anthropic",
                "api_key": "sk-..."
            })
            ```

        """
        # AI-DEV-NOTE: from_properties() is a per-component config-ASSEMBLY seam,
        # not an env-var workaround. Env-var overlay is its most common use today,
        # not the reason it exists — subclasses also dispatch on a field (e.g.
        # LLMServiceConfiguration on `provider`), apply layered fallbacks, resolve
        # secrets, and enrich fields after validation. Consequences for anyone
        # changing this: (1) do NOT assume declarative env loading (pydantic-settings)
        # would make these overrides deletable; (2) do NOT hoist error-translation
        # into this base class — assembly is component-specific and stays in each
        # subclass, so each owns its own error contract. When reasoning about WHY this
        # seam exists, read the hardest subclass, not the simplest (which is mostly
        # env-merge and misleads you into thinking the seam is removable).
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

        Subclasses override this method to assemble the validated config from raw
        inputs — overlaying environment variables is one common case, but assembly
        also covers dispatching on a field (e.g. ``GitHubConnectorConfig`` branches
        on ``auth_method``), resolving secrets, reading the filesystem, and enriching
        frozen fields after validation.

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
        # AI-DEV-NOTE: from_properties() is a per-component config-ASSEMBLY seam,
        # not an env-var workaround. Env-var overlay is its most common use today,
        # not the reason it exists — subclasses also dispatch on a field (e.g.
        # GitHubConnectorConfig on `auth_method`), resolve secrets, read the
        # filesystem, and enrich frozen fields after validation. Consequences for
        # anyone changing this: (1) do NOT assume declarative env loading
        # (pydantic-settings) would make these overrides deletable; (2) do NOT hoist
        # error-translation into this base class — assembly is component-specific and
        # stays in each subclass, so each owns its own error contract. When reasoning
        # about WHY this seam exists, read the hardest subclass, not the simplest
        # (which is mostly env-merge and misleads you into thinking the seam is
        # removable).
        return cls.model_validate(properties)
