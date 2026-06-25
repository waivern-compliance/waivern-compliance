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

        See: libs/waivern-core/docs/di-factory-patterns.md for detailed comparison.

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
        ...         return PersonalDataAnalyser(analyser_config)
        ...
        ...     def can_create(self, config: ComponentConfig) -> bool:
        ...         try:
        ...             PersonalDataAnalyserConfig.from_properties(config)
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

        ``create()`` must let the config's translated error propagate. Do NOT gate it
        on ``can_create()`` (e.g. ``if not self.can_create(config): raise
        ValueError(...)``): that collapses the precise category error into a generic
        one and hides the validation detail from the caller. ``can_create()`` is the
        boolean shadow for graceful degradation; ``create()`` is the path that
        surfaces *why* a configuration is invalid.

        Args:
            config: Configuration dict from runbook properties.
                   Factory validates and converts to typed config internally.

        Returns:
            Configured component instance ready for execution.

        Raises:
            ConnectorConfigError | ProcessorConfigError: If the configuration is
                invalid (connectors raise the former, processors the latter).
            RuntimeError: If component creation fails (e.g., service unavailable).

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

        This is the non-constructing boolean shadow of ``create()``'s preconditions:
        it reports yes/no only and MUST NOT build the component (a connector may open
        a socket or database connection in ``__init__``), so it cannot be defined as
        "try ``create()``". Implement it as ``try: <checks>; return True`` /
        ``except Exception: return False`` over the same preconditions ``create()``
        requires, allowing the caller to degrade gracefully when they do not hold.

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
            {"artifact_store": ArtifactStore}

        """
        return {}
