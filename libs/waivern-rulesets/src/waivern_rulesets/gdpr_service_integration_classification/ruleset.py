"""GDPR service integration classification ruleset.

This module defines a ruleset for classifying service integration indicators
according to GDPR requirements. It maps service category slugs to GDPR-specific
purpose categories and article references.
"""

from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator
from waivern_core import RulesetData

from waivern_rulesets.core.base import YAMLRuleset
from waivern_rulesets.types import GDPRClassificationRule


class GDPRServiceIntegrationClassificationRule(GDPRClassificationRule):
    """GDPR service integration classification rule.

    Maps service integration indicator categories to GDPR-specific classifications.
    Unlike detection rules, these rules don't have patterns - they map from
    service category slugs to GDPR purpose categories.
    """

    purpose_category: str = Field(
        description="GDPR purpose category for reporting (e.g., 'operational', 'context_dependent')",
    )
    indicator_service_categories: tuple[str, ...] = Field(
        min_length=1,
        description="Service category slugs this rule classifies (from indicator)",
    )
    typical_lawful_bases: tuple[str, ...] = Field(
        min_length=1,
        description="Typical GDPR Article 6 lawful bases for this processing",
    )
    sensitive_purpose: bool = Field(
        default=False,
        description="Whether this purpose category is privacy-sensitive",
    )
    dpia_recommendation: Literal["required", "recommended", "not_required"] = Field(
        default="not_required",
        description="DPIA recommendation level for this purpose category",
    )

    @field_validator(
        "article_references",
        "indicator_service_categories",
        "typical_lawful_bases",
        mode="before",
    )
    @classmethod
    def convert_list_to_tuple(cls, v: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v


class GDPRServiceIntegrationClassificationRulesetData(
    RulesetData[GDPRServiceIntegrationClassificationRule]
):
    """GDPR service integration classification ruleset data with validation."""

    # Master list of valid purpose categories (for reporting/governance)
    purpose_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid GDPR purpose categories",
    )

    # Valid service category slugs that can be mapped
    indicator_service_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid service category slugs from indicator",
    )

    # Sensitive categories subset
    sensitive_categories: list[str] = Field(
        default_factory=list,
        description="Subset of purpose_categories considered privacy-sensitive",
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "GDPRServiceIntegrationClassificationRulesetData":
        """Validate all rules against master lists."""
        valid_cats = set(self.purpose_categories)
        valid_service_cats = set(self.indicator_service_categories)
        sensitive_cats = set(self.sensitive_categories)

        # Validate sensitive_categories is subset of purpose_categories
        invalid_sensitive = sensitive_cats - valid_cats
        if invalid_sensitive:
            msg = (
                f"sensitive_categories contains invalid categories: {invalid_sensitive}. "
                f"Must be subset of purpose_categories: {valid_cats}"
            )
            raise ValueError(msg)

        for rule in self.rules:
            # Validate purpose_category
            if rule.purpose_category not in valid_cats:
                msg = (
                    f"Rule '{rule.name}' has invalid purpose_category "
                    f"'{rule.purpose_category}'. Valid: {valid_cats}"
                )
                raise ValueError(msg)

            # Validate indicator_service_categories
            invalid_cats = [
                cat
                for cat in rule.indicator_service_categories
                if cat not in valid_service_cats
            ]
            if invalid_cats:
                msg = (
                    f"Rule '{rule.name}' has invalid indicator_service_categories: "
                    f"{invalid_cats}. Valid: {valid_service_cats}"
                )
                raise ValueError(msg)

            # Validate sensitive_purpose matches sensitive_categories
            is_sensitive = rule.purpose_category in sensitive_cats
            if rule.sensitive_purpose != is_sensitive:
                msg = (
                    f"Rule '{rule.name}' has sensitive_purpose={rule.sensitive_purpose} "
                    f"but purpose_category '{rule.purpose_category}' "
                    f"{'is' if is_sensitive else 'is not'} in sensitive_categories"
                )
                raise ValueError(msg)

        return self


class GDPRServiceIntegrationClassificationRuleset(
    YAMLRuleset[GDPRServiceIntegrationClassificationRule]
):
    """GDPR service integration classification ruleset.

    Provides classification mappings for service integration indicators,
    enriching findings with GDPR-specific information.
    """

    ruleset_name: ClassVar[str] = "gdpr_service_integration_classification"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[GDPRServiceIntegrationClassificationRulesetData]
    ] = GDPRServiceIntegrationClassificationRulesetData
