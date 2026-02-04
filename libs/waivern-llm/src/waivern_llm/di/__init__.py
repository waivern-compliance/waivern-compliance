"""Dependency Injection configuration for LLM services.

This package provides configuration classes for LLM services that integrate
with the waivern-core DI system.

For DI integration with the LLM service, use LLMServiceFactory:

    from waivern_llm import LLMServiceFactory, LLMService
    from waivern_llm.di import LLMServiceConfiguration

    # Create factory with configuration
    factory = LLMServiceFactory(container, config)
    service = factory.create()

"""

from .configuration import LLMServiceConfiguration

__all__ = [
    "LLMServiceConfiguration",
]
