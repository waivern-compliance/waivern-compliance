"""Service integrations ruleset for detecting third-party service usage.

This module defines patterns for detecting third-party service integrations
in source code, such as cloud platforms, payment processors, analytics services,
and communication tools. These patterns are optimized for structured analysis
of imports, class names, and function names.
"""

from typing import ClassVar

from pydantic import Field, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class ServiceIntegrationRule(DetectionRule):
    """Service integration rule with service category and purpose."""

    service_category: str = Field(description="Category of service integration")
    purpose_category: str = Field(description="Purpose category for compliance")


class ServiceIntegrationsRulesetData(RulesetData[ServiceIntegrationRule]):
    """Service integrations ruleset data model."""

    # Ruleset-specific properties
    service_categories: list[str] = Field(
        min_length=1, description="Master list of valid service integration categories"
    )
    purpose_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid purpose categories for service integrations",
    )

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "ServiceIntegrationsRulesetData":
        """Validate all rule service_category and purpose_category values against master lists."""
        valid_service_categories = set(self.service_categories)
        valid_purpose_categories = set(self.purpose_categories)

        for rule in self.rules:
            if rule.service_category not in valid_service_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid service_category '{rule.service_category}'. Valid: {valid_service_categories}"
                )
            if rule.purpose_category not in valid_purpose_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid purpose_category '{rule.purpose_category}'. Valid: {valid_purpose_categories}"
                )
        return self


class ServiceIntegrationsRuleset(YAMLRuleset[ServiceIntegrationRule]):
    """Ruleset for detecting third-party service integrations in source code.

    Service integrations are critical for GDPR compliance as they represent
    data processor relationships that require data processing agreements.
    """

    ruleset_name: ClassVar[str] = "service_integrations"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[ServiceIntegrationsRulesetData]
    ] = ServiceIntegrationsRulesetData
