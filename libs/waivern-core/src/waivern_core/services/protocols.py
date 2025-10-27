"""Service protocols for dependency injection."""

from typing import Protocol


class ServiceFactory[T](Protocol):
    """Protocol for service factories that create infrastructure service instances.

    This protocol is used for infrastructure services like LLM clients, database
    connection pools, HTTP clients, and cache services. These are singleton
    services managed by the ServiceContainer.

    Note:
        For WCF components (Analysers and Connectors), use the ComponentFactory
        ABC instead. ComponentFactory provides richer metadata (schemas, runbook
        names, config validation) that components need but services don't.

        See: docs/architecture/di-factory-patterns.md for detailed comparison.

    """

    def create(self) -> T | None:
        """Create a service instance.

        Returns:
            Service instance, or None if service unavailable.

        """
        ...

    def can_create(self) -> bool:
        """Check if factory can create service instance.

        Returns:
            True if service is available and can be created, False otherwise.

        """
        ...
