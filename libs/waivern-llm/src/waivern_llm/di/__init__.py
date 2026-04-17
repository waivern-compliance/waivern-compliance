"""Dependency Injection configuration for LLM services.

This package provides configuration classes for LLM services that integrate
with the waivern-core DI system.

For DI integration with the dispatcher, use :class:`LLMDispatcherFactory`:

    from waivern_llm import LLMDispatcher, LLMDispatcherFactory
    from waivern_llm.di import LLMServiceConfiguration

    # Create factory with configuration
    factory = LLMDispatcherFactory(container, config)
    dispatcher = factory.create()

"""

from .configuration import LLMServiceConfiguration

__all__ = [
    "LLMServiceConfiguration",
]
