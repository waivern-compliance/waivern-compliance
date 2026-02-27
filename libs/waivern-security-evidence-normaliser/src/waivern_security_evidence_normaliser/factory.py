"""Factory for creating SecurityEvidenceNormaliser instances."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_rulesets.security_evidence_domain_mapping import (
    SecurityEvidenceDomainMappingRule,
)

from .analyser import SecurityEvidenceNormaliser
from .types import SecurityEvidenceNormaliserConfig


class SecurityEvidenceNormaliserFactory(ComponentFactory[SecurityEvidenceNormaliser]):
    """Factory for creating SecurityEvidenceNormaliser instances.

    No LLM service dependency — SecurityEvidenceNormaliser is fully deterministic.
    The factory only validates config structure and domain ruleset availability.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container (unused; retained for DI protocol consistency)

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> SecurityEvidenceNormaliser:
        """Create SecurityEvidenceNormaliser instance.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured SecurityEvidenceNormaliser instance

        Raises:
            ValueError: If configuration is invalid or ruleset cannot be loaded

        """
        if not self.can_create(config):
            raise ValueError("Cannot create analyser with given configuration")

        analyser_config = SecurityEvidenceNormaliserConfig.from_properties(config)
        return SecurityEvidenceNormaliser(config=analyser_config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create analyser with given configuration.

        Validates:
        1. Configuration structure and required fields
        2. Domain mapping ruleset exists and can be loaded

        Args:
            config: Configuration dict to validate

        Returns:
            True if factory can create analyser, False otherwise

        """
        try:
            analyser_config = SecurityEvidenceNormaliserConfig.from_properties(config)
        except Exception:
            return False

        try:
            RulesetManager.get_rules(
                analyser_config.domain_ruleset, SecurityEvidenceDomainMappingRule
            )
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[SecurityEvidenceNormaliser]:
        """Get the component class this factory creates."""
        return SecurityEvidenceNormaliser

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        SecurityEvidenceNormaliser has no service dependencies — it is
        fully deterministic with a YAML domain mapping ruleset.

        Returns:
            Empty dict (no service dependencies)

        """
        return {}
