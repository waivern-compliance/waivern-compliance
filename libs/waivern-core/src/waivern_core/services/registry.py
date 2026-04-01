"""Component registry for centralised component discovery.

The ComponentRegistry provides a single source of truth for component
discovery via entry points. It wraps the ServiceContainer and provides
lazy-loaded access to connector, processor, and dispatcher factories.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from importlib.metadata import entry_points

from waivern_core.base_connector import Connector
from waivern_core.base_processor import Processor
from waivern_core.component_factory import ComponentFactory
from waivern_core.dispatch import (
    DispatcherFactory,
    DispatchRequest,
    DispatchResult,
    RequestDispatcher,
)
from waivern_core.services.container import ServiceContainer

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """Centralises component discovery and factory management.

    ComponentRegistry discovers connector, processor, and dispatcher factories from
    entry points and provides unified access for all consumers (Planner, Executor,
    CLI commands).

    Discovery is lazy - factories are only instantiated on first access to
    connector_factories, processor_factories, or dispatcher_factories properties.

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
        self._processor_factories: dict[str, ComponentFactory[Processor]] | None = None
        self._dispatcher_factories: (
            dict[str, DispatcherFactory[DispatchRequest, DispatchResult]] | None
        ) = None

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
    def processor_factories(self) -> Mapping[str, ComponentFactory[Processor]]:
        """Get discovered processor factories (lazy discovery)."""
        if self._processor_factories is None:
            self._discover_components()
        return self._processor_factories  # type: ignore[return-value]

    @property
    def dispatcher_factories(
        self,
    ) -> Mapping[str, DispatcherFactory[DispatchRequest, DispatchResult]]:
        """Get discovered dispatcher factories (lazy discovery)."""
        if self._dispatcher_factories is None:
            self._discover_components()
        return self._dispatcher_factories  # type: ignore[return-value]

    def get_dispatcher_for(
        self, request_type: type[DispatchRequest]
    ) -> RequestDispatcher[DispatchRequest, DispatchResult]:
        """Resolve a dispatcher for the given request type.

        Iterates discovered dispatcher factories and returns a dispatcher
        from the first factory whose ``request_type`` matches.

        Args:
            request_type: The concrete ``DispatchRequest`` subclass to
                dispatch.

        Raises:
            ValueError: If no registered factory handles this request type.
            RuntimeError: If a matching factory cannot create a dispatcher
                (e.g., missing API key or required service).

        """
        for name, factory in self.dispatcher_factories.items():
            if factory.request_type is not request_type:
                continue

            if not factory.can_create():
                msg = (
                    f"Dispatcher factory '{name}' matches request type "
                    f"'{request_type.__name__}' but cannot create a dispatcher"
                )
                raise RuntimeError(msg)

            dispatcher = factory.create()
            if dispatcher is None:
                msg = (
                    f"Dispatcher factory '{name}' matched request type "
                    f"'{request_type.__name__}' but create() returned None"
                )
                raise RuntimeError(msg)

            return dispatcher

        msg = f"No dispatcher factory registered for request type '{request_type.__name__}'"
        raise ValueError(msg)

    def _discover_components(self) -> None:
        """Discover connector, processor, and dispatcher factories from entry points.

        Also registers schemas from packages via waivern.schemas entry points.
        Schema registration must happen before components are used to ensure
        schema files can be found.
        """
        # Register schemas first (before component factories need them)
        self._register_schemas()

        self._connector_factories = {}
        self._processor_factories = {}
        self._dispatcher_factories = {}

        # Discover connectors
        for ep in entry_points(group="waivern.connectors"):
            factory_class = ep.load()
            factory = factory_class(self._container)
            self._connector_factories[ep.name] = factory

        # Discover processors
        for ep in entry_points(group="waivern.processors"):
            factory_class = ep.load()
            factory = factory_class(self._container)
            self._processor_factories[ep.name] = factory

        # Discover dispatchers
        for ep in entry_points(group="waivern.dispatchers"):
            factory_class = ep.load()
            factory = factory_class(self._container)
            self._dispatcher_factories[ep.name] = factory

    def _register_schemas(self) -> None:
        """Register schemas from all packages via entry points."""
        for ep in entry_points(group="waivern.schemas"):
            try:
                register_func = ep.load()
                register_func()
                logger.debug("Registered schemas from '%s'", ep.name)
            except Exception as e:
                logger.warning("Failed to register schemas from '%s': %s", ep.name, e)
