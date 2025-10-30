"""Factory for creating ProcessingPurposeAnalyser instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_llm import BaseLLMService

from .analyser import ProcessingPurposeAnalyser
from .types import ProcessingPurposeAnalyserConfig


class ProcessingPurposeAnalyserFactory(ComponentFactory[ProcessingPurposeAnalyser]):
    """Factory for creating ProcessingPurposeAnalyser instances with dependency injection.

    This factory follows the three-tier DI architecture:
    - Tier 1: Infrastructure services (BaseLLMService) injected into factory
    - Tier 2: Factory (this class) holds service references
    - Tier 3: Component instances created with injected services

    The factory validates configuration and creates analysers with:
    - LLM service for validation (optional, injected)
    - Pattern matcher instantiated from config (not a service)
    """

    def __init__(self, llm_service: BaseLLMService | None = None) -> None:
        """Initialise factory with optional LLM service.

        Args:
            llm_service: Optional LLM service for validation. If None, LLM validation
                will be disabled for created analysers.

        """
        self._llm_service = llm_service

    @override
    def create(self, config: ComponentConfig) -> ProcessingPurposeAnalyser:
        """Create ProcessingPurposeAnalyser instance with injected dependencies.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured ProcessingPurposeAnalyser instance

        Raises:
            ValueError: If configuration is invalid or requirements cannot be met

        """
        # Parse and validate configuration
        analyser_config = ProcessingPurposeAnalyserConfig.from_properties(config)

        # Validate that LLM validation requirements can be met
        if (
            analyser_config.llm_validation.enable_llm_validation
            and self._llm_service is None
        ):
            msg = "LLM validation enabled but no LLM service available"
            raise ValueError(msg)

        # Create analyser with injected LLM service
        return ProcessingPurposeAnalyser(
            config=analyser_config,
            llm_service=self._llm_service,
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create analyser with given configuration.

        Args:
            config: Configuration dict to validate

        Returns:
            True if factory can create analyser, False otherwise

        """
        # Try to parse and validate configuration
        try:
            analyser_config = ProcessingPurposeAnalyserConfig.from_properties(config)
        except Exception:
            # Config validation failed
            return False

        # If LLM validation enabled, must have LLM service
        if (
            analyser_config.llm_validation.enable_llm_validation
            and self._llm_service is None
        ):
            return False

        return True

    @override
    def get_component_name(self) -> str:
        """Get component type name for registry lookup.

        Returns:
            Component type name: "processing_purpose_analyser"

        """
        return "processing_purpose_analyser"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get input schemas accepted by created analysers.

        Returns:
            List containing StandardInputSchema and SourceCodeSchema

        """
        return ProcessingPurposeAnalyser.get_supported_input_schemas()

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get output schemas produced by created analysers.

        Returns:
            List containing ProcessingPurposeFindingSchema

        """
        return ProcessingPurposeAnalyser.get_supported_output_schemas()

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        Returns:
            Dictionary mapping dependency names to their types:
            - "llm_service": BaseLLMService (optional)

        """
        return {
            "llm_service": BaseLLMService,
        }
