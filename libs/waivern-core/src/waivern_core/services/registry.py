"""Component registry for centralised component discovery.

The ComponentRegistry provides a single source of truth for component
discovery via entry points. It wraps the ServiceContainer and provides
lazy-loaded access to connector and analyser factories.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from importlib.metadata import entry_points

from waivern_core.base_analyser import Analyser
from waivern_core.base_connector import Connector
from waivern_core.component_factory import ComponentFactory
from waivern_core.services.container import ServiceContainer

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """Centralises component discovery and factory management.

    ComponentRegistry discovers connector and analyser factories from entry points
    and provides unified access for all consumers (Planner, Executor, CLI commands).

    Discovery is lazy - factories are only instantiated on first access to
    connector_factories or analyser_factories properties.

    Example:
        >>> container = ServiceContainer()
        >>> container.register(ServiceDescriptor(ArtifactStore, store_factory, "transient"))
        >>>
        >>> registry = ComponentRegistry(container)
        >>>
        >>> planner = Planner(registry)
        >>> executor = DAGExecutor(registry)

    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise registry with service container.

        Args:
            container: ServiceContainer for factory dependency injection.

        """
        self._container = container
        self._connector_factories: dict[str, ComponentFactory[Connector]] | None = None
        self._analyser_factories: dict[str, ComponentFactory[Analyser]] | None = None

    @property
    def container(self) -> ServiceContainer:
        """Get the underlying service container."""
        return self._container

    @property
    def connector_factories(self) -> Mapping[str, ComponentFactory[Connector]]:
        """Get discovered connector factories (lazy discovery)."""
        if self._connector_factories is None:
            self._discover_components()
        return self._connector_factories  # type: ignore[return-value]

    @property
    def analyser_factories(self) -> Mapping[str, ComponentFactory[Analyser]]:
        """Get discovered analyser factories (lazy discovery)."""
        if self._analyser_factories is None:
            self._discover_components()
        return self._analyser_factories  # type: ignore[return-value]

    def _discover_components(self) -> None:
        """Discover connector and analyser factories from entry points.

        Also registers schemas from packages via waivern.schemas entry points.
        Schema registration must happen before components are used to ensure
        schema files can be found.
        """
        # Register schemas first (before component factories need them)
        self._register_schemas()

        self._connector_factories = {}
        self._analyser_factories = {}

        # Discover connectors
        for ep in entry_points(group="waivern.connectors"):
            factory_class = ep.load()
            factory = factory_class(self._container)
            self._connector_factories[ep.name] = factory

        # Discover analysers
        for ep in entry_points(group="waivern.analysers"):
            factory_class = ep.load()
            factory = factory_class(self._container)
            self._analyser_factories[ep.name] = factory

    def _register_schemas(self) -> None:
        """Register schemas from all packages via entry points."""
        for ep in entry_points(group="waivern.schemas"):
            try:
                register_func = ep.load()
                register_func()
                logger.debug("Registered schemas from '%s'", ep.name)
            except Exception as e:
                logger.warning("Failed to register schemas from '%s': %s", ep.name, e)
