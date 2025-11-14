"""Service protocols for dependency injection."""

from typing import Protocol


class ServiceFactory[T](Protocol):
    """Protocol for service factories that create infrastructure service instances.

    This protocol is used for infrastructure services like LLM clients, database
    connection pools, HTTP clients, and cache services. These are singleton
    services managed by the ServiceContainer.

    Configuration Pattern:
        ServiceFactory implementations MAY accept optional configuration in their
        constructor to support both programmatic configuration and environment-based
        configuration with fallback.

        Two valid patterns:
        1. Environment-only (zero-config):
           ```python
           factory = LLMServiceFactory()  # Reads from env vars
           ```

        2. Explicit config with env fallback:
           ```python
           config = LLMServiceConfiguration(provider="anthropic", api_key="sk-...")
           factory = LLMServiceFactory(config)  # Uses config, falls back to env
           ```

        The protocol methods (create, can_create) take NO parameters. Configuration
        is held by the factory instance, not passed per-call.

    Comparison with ComponentFactory:
        - ServiceFactory: Infrastructure services (singleton), create() takes NO config
        - ComponentFactory: WCF components (transient), create(config) takes config dict

        See: docs/architecture/di-factory-patterns.md for detailed comparison.

    Example:
        ```python
        from waivern_core.services import BaseServiceConfiguration

        class LLMServiceConfiguration(BaseServiceConfiguration):
            provider: str
            api_key: str

        class LLMServiceFactory:
            def __init__(self, config: LLMServiceConfiguration | None = None):
                self._config = config  # Optional - can be None

            def can_create(self) -> bool:
                # Use config if provided, otherwise try environment
                config = self._config or self._try_config_from_env()
                return config is not None

            def create(self) -> BaseLLMService | None:
                config = self._config or self._try_config_from_env()
                if not config:
                    return None
                return BaseLLMService(config.provider, config.api_key)
        ```

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


class ServiceProvider(Protocol):
    """Protocol for service providers that wrap ServiceContainer.

    Service providers offer a higher-level, exception-safe API for retrieving
    services from a ServiceContainer. Unlike calling container.get_service()
    directly (which raises exceptions), providers return None for unavailable
    services, enabling graceful degradation.

    Naming Note:
        WCF's ServiceProvider differs from .NET's IServiceProvider:
        - .NET IServiceProvider: IS the DI container itself
        - WCF ServiceProvider: Optional wrapper around ServiceContainer for cleaner APIs

        WCF's ServiceContainer is equivalent to .NET's IServiceProvider.

    When to implement ServiceProvider:
        - Standalone packages meant for external/third-party use (e.g., waivern-llm)
        - Services that may be used outside WCF ecosystem
        - Packages that want to hide ServiceContainer complexity

    When NOT to implement ServiceProvider:
        - WCF-internal services (e.g., ArtifactStore used only by Executor)
        - Services only accessed within WCF components
        - When ServiceContainer direct access is acceptable

    This protocol enables:
        - Exception-free service retrieval (returns None instead of raising)
        - Availability checking without attempting service creation
        - Type-safe generic service access
        - Consistent pattern across different service types

    Example:
        ```python
        class LLMServiceProvider(ServiceProvider):
            def __init__(self, container: ServiceContainer):
                self._container = container

            def get_service[T](self, service_type: type[T]) -> T | None:
                try:
                    return self._container.get_service(service_type)
                except (ValueError, KeyError):
                    return None

            def is_available[T](self, service_type: type[T]) -> bool:
                service = self.get_service(service_type)
                return service is not None
        ```

    See Also:
        ServiceFactory: Protocol for creating service instances
        ServiceContainer: Container managing service lifecycle

    """

    def get_service[T](self, service_type: type[T]) -> T | None:
        """Get service instance from container, or None if unavailable.

        This method wraps the container's get_service() and handles all
        exceptions gracefully, returning None instead. This enables
        optional dependencies and graceful degradation patterns.

        Args:
            service_type: The type of service to retrieve

        Returns:
            Service instance, or None if service unavailable or not registered

        Example:
            ```python
            llm_service = provider.get_service(BaseLLMService)
            if llm_service:
                result = llm_service.analyse_data(text, prompt)
            else:
                # Fall back to non-LLM analysis
                result = pattern_match_only(text)
            ```

        """
        ...

    def is_available[T](self, service_type: type[T]) -> bool:
        """Check if service type is available without retrieving it.

        This is a convenience method for checking service availability
        before attempting to use it. Implementations typically call
        get_service() and check if result is not None.

        Args:
            service_type: The type of service to check

        Returns:
            True if service is available, False otherwise

        Example:
            ```python
            if provider.is_available(BaseLLMService):
                llm_service = provider.get_service(BaseLLMService)
                result = llm_service.analyse_data(text, prompt)
            ```

        """
        ...
