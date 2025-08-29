"""Service integrations ruleset for detecting third-party service usage.

This module defines patterns for detecting third-party service integrations
in source code, such as cloud platforms, payment processors, analytics services,
and communication tools. These patterns are optimized for structured analysis
of imports, class names, and function names.
"""

import logging
from pathlib import Path
from typing import Final, override

import yaml

from wct.rulesets.base import Ruleset
from wct.rulesets.types import ServiceIntegrationRule, ServiceIntegrationsRulesetData

logger = logging.getLogger(__name__)

# Version constant for this ruleset and its data (private)
_RULESET_DATA_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "service_integrations"


class ServiceIntegrationsRuleset(Ruleset[ServiceIntegrationRule]):
    """Ruleset for detecting third-party service integrations in source code.

    This ruleset focuses on identifying service integrations through:
    - Import statements (e.g., 'import stripe')
    - Class names (e.g., 'StripePaymentProcessor')
    - Function names (e.g., 'sendViaMailchimp')
    - Configuration references (e.g., 'STRIPE_API_KEY')

    Service integrations are critical for GDPR compliance as they represent
    data processor relationships that require data processing agreements.
    """

    def __init__(self) -> None:
        """Initialise the service integrations ruleset."""
        self._rules: tuple[ServiceIntegrationRule, ...] | None = None
        logger.debug(f"Initialised {self.name} ruleset version {self.version}")

    @property
    @override
    def name(self) -> str:
        """Get the canonical name of this ruleset."""
        return _RULESET_NAME

    @property
    @override
    def version(self) -> str:
        """Get the version of this ruleset."""
        return _RULESET_DATA_VERSION

    @override
    def get_rules(self) -> tuple[ServiceIntegrationRule, ...]:
        """Get the service integration rules.

        Returns:
            Immutable tuple of ServiceIntegrationRule objects containing all service integration patterns

        """
        if self._rules is None:
            # Load from external configuration file with validation
            ruleset_file = (
                Path(__file__).parent
                / "data"
                / _RULESET_NAME
                / _RULESET_DATA_VERSION
                / f"{_RULESET_NAME}.yaml"
            )
            with ruleset_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            ruleset_data = ServiceIntegrationsRulesetData.model_validate(data)
            self._rules = tuple(ruleset_data.rules)
            logger.debug(f"Loaded {len(self._rules)} service integration patterns")

        return self._rules
