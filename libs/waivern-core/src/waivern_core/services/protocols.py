"""Service protocols for dependency injection."""

from typing import Protocol


class ServiceFactory[T](Protocol):
    """Protocol for service factories that create service instances."""

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
