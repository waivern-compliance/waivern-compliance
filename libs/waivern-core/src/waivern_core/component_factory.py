"""Component factory abstraction for DI-enabled component creation.

This module provides the ComponentFactory ABC that all analyser and connector
factories must implement. ComponentFactory bridges the gap between:
- Infrastructure services (singleton, managed by DI container)
- Component instances (transient, created per execution)

ComponentFactory instances are singleton services that create transient
component instances (analysers/connectors) with injected dependencies.

Example:
    >>> # Infrastructure service (singleton)
    >>> llm_service = container.get_service(BaseLLMService)
    >>>
    >>> # Component factory (singleton) with injected dependencies
    >>> factory = PersonalDataAnalyserFactory(llm_service=llm_service)
    >>>
    >>> # Component configuration dict (from runbook properties)
    >>> config = {"pattern_matching": {"ruleset": "personal_data"}}
    >>>
    >>> # Component instance (transient) created by factory
    >>> analyser = factory.create(config)

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from waivern_core.schemas import Schema

type ComponentConfig = dict[str, Any]


class ComponentFactory[T](ABC):
    """Abstract base class for component factories that create DI-enabled WCF components.

    ComponentFactory is the bridge between:
    - Tier 1: Infrastructure services (singleton) - LLM, database, cache
    - Tier 2: Component factories (singleton) - hold references to services
    - Tier 3: Component instances (transient) - created per execution

    All analyser and connector factories must implement this interface to enable:
    - Dependency injection of infrastructure services
    - Schema-based component discovery and matching
    - Configuration validation before instantiation
    - Health checking for remote/SaaS components
    - AI agent discovery and querying

    Note:
        This abstraction is specifically for WCF components (Analysers and Connectors).
        For infrastructure services (LLM, database pools, HTTP clients), use the
        ServiceFactory protocol instead.

        See: docs/architecture/di-factory-patterns.md for detailed comparison.

    Type Parameters:
        T: The component type this factory creates (Analyser or Connector)

    Example:
        >>> class PersonalDataAnalyserFactory(ComponentFactory[PersonalDataAnalyser]):
        ...     def __init__(self, llm_service: BaseLLMService | None = None):
        ...         self._llm_service = llm_service
        ...
        ...     def create(self, config: ComponentConfig) -> PersonalDataAnalyser:
        ...         analyser_config = PersonalDataAnalyserConfig.from_properties(config)
        ...         return PersonalDataAnalyser(analyser_config, self._llm_service)
        ...
        ...     def get_component_name(self) -> str:
        ...         return "personal_data_analyser"
        ...
        ...     def get_input_schemas(self) -> list[Schema]:
        ...         return [Schema("standard_input", "1.0.0")]
        ...
        ...     def get_output_schemas(self) -> list[Schema]:
        ...         return [Schema("personal_data_finding", "1.0.0")]
        ...
        ...     def can_create(self, config: ComponentConfig) -> bool:
        ...         # Validate config and check service availability
        ...         try:
        ...             analyser_config = PersonalDataAnalyserConfig.from_properties(config)
        ...             if analyser_config.llm_validation.enable_llm_validation:
        ...                 return self._llm_service is not None
        ...             return True
        ...         except Exception:
        ...             return False

    """

    @abstractmethod
    def create(self, config: ComponentConfig) -> T:
        """Create a component instance with the given configuration.

        This method creates a transient component instance (analyser or connector)
        with execution-specific configuration. The factory injects any required
        infrastructure services (LLM, database, cache) into the component.

        Args:
            config: Configuration dict from runbook properties.
                   Factory validates and converts to typed config internally.

        Returns:
            Configured component instance ready for execution.

        Raises:
            ValueError: If configuration is invalid or missing required fields
            RuntimeError: If component creation fails (e.g., service unavailable)

        Example:
            >>> factory = PersonalDataAnalyserFactory(llm_service)
            >>> config = {
            ...     "pattern_matching": {"ruleset": "personal_data"},
            ...     "llm_validation": {"enable_llm_validation": True}
            ... }
            >>> analyser = factory.create(config)

        """
        ...

    @abstractmethod
    def get_component_name(self) -> str:
        """Get the component type name used in runbooks.

        This name is used in runbook YAML files to identify which component
        type to use. It must be unique across all components of the same kind
        (analyser or connector).

        Returns:
            Component type name (e.g., "personal_data_analyser", "mysql")

        Example:
            >>> factory.get_component_name()
            'personal_data_analyser'

        """
        ...

    @abstractmethod
    def get_input_schemas(self) -> list[Schema]:
        """Get the list of input schemas this component supports.

        The executor uses this for schema-based component matching. A component
        can support multiple input schemas if it can handle different data formats.

        Returns:
            List of Schema objects this component can process.

        Example:
            >>> factory.get_input_schemas()
            [Schema("standard_input", "1.0.0"), Schema("source_code", "1.0.0")]

        """
        ...

    @abstractmethod
    def get_output_schemas(self) -> list[Schema]:
        """Get the list of output schemas this component produces.

        The executor uses this for schema-based component chaining. A component
        can produce multiple output schemas if it generates different finding types.

        Returns:
            List of Schema objects this component produces.

        Example:
            >>> factory.get_output_schemas()
            [PersonalDataFindingSchema()]

        """
        ...

    @abstractmethod
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if component can be created with the given configuration.

        This method validates:
        - Configuration structure and required fields
        - Service availability (e.g., LLM service available if needed)
        - Remote service health (for SaaS wrappers)
        - Any other prerequisites for component creation

        This is called by the executor before attempting to create the component,
        allowing graceful degradation when services are unavailable.

        Args:
            config: Configuration to validate (from runbook properties)

        Returns:
            True if component can be created with this config, False otherwise

        Example:
            >>> config = {"pattern_matching": {"ruleset": "personal_data"}}
            >>> factory.can_create(config)
            True
            >>> bad_config = {}
            >>> factory.can_create(bad_config)
            False

        """
        ...

    def get_service_dependencies(self) -> dict[str, type]:
        """Get optional mapping of service dependencies for this factory.

        This method declares which infrastructure services this factory needs.
        It's used for documentation and future auto-wiring capabilities.

        The default implementation returns an empty dict (no dependencies).
        Override this method if your factory requires infrastructure services.

        Returns:
            Dict mapping dependency names to service types.
            Empty dict if no dependencies.

        Example:
            >>> factory.get_service_dependencies()
            {"llm_service": BaseLLMService}

        """
        return {}
