"""Component factory abstraction for DI-enabled component creation.

This module provides the ComponentFactory ABC that all analyser and connector
factories must implement. ComponentFactory bridges the gap between:
- Infrastructure services (singleton, managed by DI container)
- Component instances (transient, created per execution)

ComponentFactory instances are singleton services that create transient
component instances (analysers/connectors) by resolving dependencies from
the ServiceContainer.

Example:
    >>> # Component factory (singleton) receives container
    >>> factory = PersonalDataAnalyserFactory(container)
    >>>
    >>> # Component configuration dict (from runbook properties)
    >>> config = {"pattern_matching": {"ruleset": "local/personal_data/1.0.0"}}
    >>>
    >>> # Component instance (transient) created by factory
    >>> # Factory resolves dependencies from container internally
    >>> analyser = factory.create(config)

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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

    Service Locator Pattern:
        ComponentFactory uses Service Locator pattern - factories receive ServiceContainer
        and call get_service() to resolve dependencies dynamically. This is appropriate for
        WCF's plugin architecture where:
        - Factories are discovered at runtime via entry points
        - Dependencies may be optional (graceful degradation required)
        - Component creation is configuration-driven from runbook properties

        See: ADR-0002 "Service Locator in Component Factories" for architectural justification.

    Note:
        This abstraction is specifically for WCF components (Analysers and Connectors).
        For infrastructure services (LLM, database pools, HTTP clients), use the
        ServiceFactory protocol instead.

        See: docs/architecture/di-factory-patterns.md for detailed comparison.

    Type Parameters:
        T: The component type this factory creates (Analyser or Connector)

    Example:
        >>> class PersonalDataAnalyserFactory(ComponentFactory[PersonalDataAnalyser]):
        ...     def __init__(self, container: ServiceContainer):
        ...         self._container = container
        ...
        ...     @property
        ...     def component_class(self) -> type[PersonalDataAnalyser]:
        ...         return PersonalDataAnalyser
        ...
        ...     def create(self, config: ComponentConfig) -> PersonalDataAnalyser:
        ...         analyser_config = PersonalDataAnalyserConfig.from_properties(config)
        ...         # Resolve dependencies from container
        ...         try:
        ...             llm_service = self._container.get_service(LLMService)
        ...         except ValueError:
        ...             llm_service = None
        ...         return PersonalDataAnalyser(analyser_config, llm_service)
        ...
        ...     def can_create(self, config: ComponentConfig) -> bool:
        ...         # Validate config and check service availability
        ...         try:
        ...             analyser_config = PersonalDataAnalyserConfig.from_properties(config)
        ...             if analyser_config.llm_validation.enable_llm_validation:
        ...                 # Check if service is available in container
        ...                 try:
        ...                     self._container.get_service(LLMService)
        ...                     return True
        ...                 except ValueError:
        ...                     return False
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
            >>> factory = PersonalDataAnalyserFactory(container)
            >>> config = {
            ...     "pattern_matching": {"ruleset": "local/personal_data/1.0.0"},
            ...     "llm_validation": {"enable_llm_validation": True}
            ... }
            >>> analyser = factory.create(config)

        """
        ...

    @property
    @abstractmethod
    def component_class(self) -> type[T]:
        """Get the component class this factory creates.

        This property provides access to the component class for calling
        class methods like get_name(), get_input_requirements(), and
        get_supported_output_schemas() without instantiating the component.

        Returns:
            The component class type.

        Example:
            >>> factory.component_class.get_name()
            'personal_data_analyser'
            >>> factory.component_class.get_input_requirements()
            [[InputRequirement("standard_input", "1.0.0")]]
            >>> factory.component_class.get_supported_output_schemas()
            [Schema("personal_data_finding", "1.0.0")]

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
            >>> config = {"pattern_matching": {"ruleset": "local/personal_data/1.0.0"}}
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
            {"llm_service": LLMService}

        """
        return {}
