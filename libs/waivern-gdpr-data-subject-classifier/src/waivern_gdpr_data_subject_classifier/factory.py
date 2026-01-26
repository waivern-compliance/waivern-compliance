"""Factory for creating GDPRDataSubjectClassifier instances."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_llm import BaseLLMService
from waivern_rulesets import GDPRDataSubjectClassificationRule

from .classifier import GDPRDataSubjectClassifier
from .types import GDPRDataSubjectClassifierConfig


class GDPRDataSubjectClassifierFactory(ComponentFactory[GDPRDataSubjectClassifier]):
    """Factory for creating GDPRDataSubjectClassifier instances.

    This factory parses configuration from runbook properties and creates
    classifiers with the specified ruleset URI.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container (not used but required by interface)

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> GDPRDataSubjectClassifier:
        """Create GDPRDataSubjectClassifier instance with injected dependencies.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured GDPRDataSubjectClassifier instance

        Raises:
            ValueError: If configuration is invalid or requirements cannot be met

        """
        if not self.can_create(config):
            raise ValueError("Cannot create classifier with given configuration")

        classifier_config = GDPRDataSubjectClassifierConfig.from_properties(config)

        # Safe to resolve - can_create() already validated availability
        llm_service = (
            self._container.get_service(BaseLLMService)
            if classifier_config.llm_validation.enable_llm_validation
            else None
        )

        return GDPRDataSubjectClassifier(
            config=classifier_config,
            llm_service=llm_service,
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create classifier with given configuration.

        Validates:
        1. Configuration structure and required fields
        2. Ruleset exists and can be loaded
        3. LLM service available (if LLM validation enabled)

        Args:
            config: Configuration dict to validate

        Returns:
            True if configuration is valid and ruleset exists, False otherwise

        """
        try:
            classifier_config = GDPRDataSubjectClassifierConfig.from_properties(config)
        except Exception:
            return False

        # Validate ruleset exists
        try:
            RulesetManager.get_ruleset(
                classifier_config.ruleset, GDPRDataSubjectClassificationRule
            )
        except Exception:
            return False

        # If LLM validation enabled, must have LLM service available in container
        if classifier_config.llm_validation.enable_llm_validation:
            try:
                self._container.get_service(BaseLLMService)
            except (ValueError, KeyError):
                return False

        return True

    @property
    @override
    def component_class(self) -> type[GDPRDataSubjectClassifier]:
        """Get the component class this factory creates."""
        return GDPRDataSubjectClassifier

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        Returns:
            Dictionary mapping dependency names to their types.
            Includes BaseLLMService for optional LLM validation.

        """
        return {"llm_service": BaseLLMService}
