"""Utility for managing LLM service lifecycle."""

import logging

from wct.llm_service import BaseLLMService, LLMServiceError, LLMServiceFactory

logger = logging.getLogger(__name__)


class LLMServiceManager:
    """Utility for managing LLM service lifecycle and configuration."""

    def __init__(self, enable_llm_validation: bool = True) -> None:
        """Initialise the LLM service manager.

        Args:
            enable_llm_validation: Whether to enable LLM validation

        """
        self._enable_llm_validation = enable_llm_validation
        self._llm_service: BaseLLMService | None = None

    @property
    def llm_service(self) -> BaseLLMService | None:
        """Get the LLM service, creating it if necessary."""
        if self._llm_service is None and self._enable_llm_validation:
            try:
                self._llm_service = LLMServiceFactory.create_anthropic_service()
                logger.info("LLM service initialised for compliance analysis")
            except LLMServiceError as e:
                logger.warning(
                    f"Failed to initialise LLM service: {e}. Continuing without LLM validation."
                )
                self._enable_llm_validation = False
        return self._llm_service
