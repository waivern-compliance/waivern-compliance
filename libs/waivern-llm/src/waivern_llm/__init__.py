"""Multi-provider LLM abstraction for Waivern Compliance Framework.

The primary LLM service API is available via the v2 subpackage:

    from waivern_llm.v2 import LLMService, LLMServiceFactory

This module exports shared error types used across the package.
"""

__version__ = "0.1.0"

from waivern_llm.errors import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMServiceError,
)

__all__ = [
    # Version
    "__version__",
    # Errors
    "LLMServiceError",
    "LLMConfigurationError",
    "LLMConnectionError",
]
