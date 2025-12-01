"""Dependency Injection integration for LLM services.

This package provides DI adapters that integrate waivern-llm services with the
waivern-core dependency injection container. The core LLM services remain pure
and independent, while this package provides optional DI integration.

Architecture:
    - waivern_llm.base, anthropic, etc: Pure LLM services (no DI knowledge)
    - waivern_llm.di: Optional DI adapters for container integration

Components:
    - LLMServiceFactory: ServiceFactory[BaseLLMService] implementation
    - LLMServiceProvider: High-level convenience API for LLM service access
    - LLMServiceConfiguration: Configuration dataclass with validation

Example usage:
    ```python
    from waivern_core.services import ServiceContainer, ServiceDescriptor
    from waivern_llm.di import LLMServiceFactory, LLMServiceProvider
    from waivern_llm.base import BaseLLMService

    # Create container and register LLM service
    container = ServiceContainer()
    container.register(
        ServiceDescriptor(BaseLLMService, LLMServiceFactory(), "singleton")
    )

    # Use provider for convenient access
    provider = LLMServiceProvider(container)
    llm_service = provider.get_llm_service()

    if provider.is_available:
        result = llm_service.generate("Analyse this data...")
    ```

See Also:
    - waivern_core.services: Generic DI infrastructure
    - ADR-0002: Dependency Injection for Service Management

"""

# Exports will be added as components are implemented:
from .configuration import LLMServiceConfiguration
from .factory import LLMServiceFactory
from .provider import LLMServiceProvider

__all__ = [
    "LLMServiceConfiguration",
    "LLMServiceFactory",
    "LLMServiceProvider",
]
