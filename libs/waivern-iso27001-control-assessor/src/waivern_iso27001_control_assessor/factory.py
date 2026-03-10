"""Factory for creating ISO27001Assessor instances."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_llm import LLMService
from waivern_rulesets.iso27001_domains import ISO27001DomainsRule

from .analyser import ISO27001Assessor
from .types import ISO27001AssessorConfig


class ISO27001AssessorFactory(ComponentFactory[ISO27001Assessor]):
    """Factory for creating ISO27001Assessor instances.

    Always resolves LLMService from the DI container — the assessor
    requires LLM for producing assessment verdicts. The per-control
    evidence_status logic (Step 4) decides whether the LLM is actually
    called for each control.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container for resolving LLMService.

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> ISO27001Assessor:
        """Create ISO27001Assessor instance with injected dependencies.

        Args:
            config: Configuration dict from runbook properties.

        Returns:
            Configured ISO27001Assessor instance.

        Raises:
            ValueError: If configuration is invalid or requirements cannot be met.

        """
        if not self.can_create(config):
            raise ValueError("Cannot create assessor with given configuration")

        assessor_config = ISO27001AssessorConfig.from_properties(config)
        llm_service = self._container.get_service(LLMService)

        return ISO27001Assessor(
            config=assessor_config,
            llm_service=llm_service,
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create assessor with given configuration.

        Validates:
        1. Configuration structure and required fields
        2. Domain ruleset exists and can be loaded
        3. LLM service is available in the container

        Args:
            config: Configuration dict to validate.

        Returns:
            True if factory can create assessor, False otherwise.

        """
        try:
            assessor_config = ISO27001AssessorConfig.from_properties(config)
        except Exception:
            return False

        try:
            RulesetManager.get_ruleset(
                assessor_config.domain_ruleset, ISO27001DomainsRule
            )
        except Exception:
            return False

        try:
            self._container.get_service(LLMService)
        except (ValueError, KeyError):
            return False

        return True

    @property
    @override
    def component_class(self) -> type[ISO27001Assessor]:
        """Get the component class this factory creates."""
        return ISO27001Assessor

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container."""
        return {"llm_service": LLMService}
