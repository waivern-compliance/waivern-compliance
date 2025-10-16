"""LLM service exceptions."""

from waivern_core.errors import WaivernError


class LLMServiceError(WaivernError):
    """Base exception for LLM service related errors."""

    pass


class LLMConfigurationError(LLMServiceError):
    """Exception raised when LLM service is misconfigured."""

    pass


class LLMConnectionError(LLMServiceError):
    """Exception raised when LLM service connection fails."""

    pass
