"""Factory for creating DataSubjectAnalyser instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_llm import BaseLLMService

from .analyser import DataSubjectAnalyser
from .types import DataSubjectAnalyserConfig


class DataSubjectAnalyserFactory(ComponentFactory[DataSubjectAnalyser]):
    """Factory for creating DataSubjectAnalyser instances with dependency injection."""

    def __init__(self, llm_service: BaseLLMService | None = None) -> None:
        """Initialise factory with optional LLM service."""
        self._llm_service = llm_service

    @override
    def create(self, config: ComponentConfig) -> DataSubjectAnalyser:
        """Create DataSubjectAnalyser instance with injected dependencies.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured DataSubjectAnalyser instance

        Raises:
            ValueError: If configuration is invalid or requirements cannot be met

        """
        # Parse and validate configuration
        analyser_config = DataSubjectAnalyserConfig.from_properties(config)

        # Validate that LLM validation requirements can be met
        if (
            analyser_config.llm_validation.enable_llm_validation
            and self._llm_service is None
        ):
            msg = "LLM validation enabled but no LLM service available"
            raise ValueError(msg)

        # Create analyser with injected LLM service
        return DataSubjectAnalyser(
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
            analyser_config = DataSubjectAnalyserConfig.from_properties(config)
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
        """Get component type name for registry lookup."""
        return "data_subject_analyser"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get input schemas accepted by created analysers."""
        return DataSubjectAnalyser.get_supported_input_schemas()

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get output schemas produced by created analysers."""
        return DataSubjectAnalyser.get_supported_output_schemas()

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container."""
        return {
            "llm_service": BaseLLMService,
        }
