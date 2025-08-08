"""Utility for managing LLM service lifecycle."""

from wct.llm_service import LLMServiceError, LLMServiceFactory
from wct.logging import get_analyser_logger


class LLMServiceManager:
    """Utility for managing LLM service lifecycle and configuration."""

    def __init__(self, enable_llm_validation: bool = True):
        """Initialize the LLM service manager.

        Args:
            enable_llm_validation: Whether to enable LLM validation
        """
        self.enable_llm_validation = enable_llm_validation
        self._llm_service = None
        self.logger = get_analyser_logger("llm_service_manager")

    @property
    def llm_service(self):
        """Get the LLM service, creating it if necessary."""
        if self._llm_service is None and self.enable_llm_validation:
            try:
                self._llm_service = LLMServiceFactory.create_anthropic_service()
                self.logger.info("LLM service initialised for compliance analysis")
            except LLMServiceError as e:
                self.logger.warning(
                    f"Failed to initialise LLM service: {e}. Continuing without LLM validation."
                )
                self.enable_llm_validation = False
        return self._llm_service

    def is_available(self) -> bool:
        """Check if LLM service is available and enabled."""
        return self.enable_llm_validation and self.llm_service is not None
