"""GDPR compliance classification ruleset.

This module defines a ruleset for classifying indicator findings
according to GDPR requirements. It maps indicator values to GDPR-specific
purpose categories and article references.
"""

from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator
from waivern_core import RulesetData

from waivern_rulesets.core.base import YAMLRuleset
from waivern_rulesets.types import GDPRClassificationRule


class GDPRComplianceClassificationRule(GDPRClassificationRule):
    """GDPR compliance classification rule.

    Maps indicator values to GDPR-specific classifications.
    Unlike detection rules, these rules don't have patterns - they map from
    indicator values to GDPR purpose categories.
    """

    purpose_category: str = Field(
        description="GDPR purpose category for reporting (e.g., 'ai_and_ml', 'operational')",
    )
    indicator_purposes: tuple[str, ...] = Field(
        min_length=1,
        description="Indicator values this rule classifies (from upstream analysers)",
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
        "indicator_purposes",
        "typical_lawful_bases",
        mode="before",
    )
    @classmethod
    def convert_list_to_tuple(cls, v: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v


class GDPRComplianceClassificationRulesetData(
    RulesetData[GDPRComplianceClassificationRule]
):
    """GDPR compliance classification ruleset data with validation."""

    # Master list of valid purpose categories (for reporting/governance)
    purpose_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid GDPR purpose categories",
    )

    # Valid indicator values that can be mapped (from upstream analysers)
    indicator_purposes: list[str] = Field(
        min_length=1,
        description="Master list of valid indicator values",
    )

    # Sensitive categories subset
    sensitive_categories: list[str] = Field(
        default_factory=list,
        description="Subset of purpose_categories considered privacy-sensitive",
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "GDPRComplianceClassificationRulesetData":
        """Validate all rules against master lists."""
        valid_cats = set(self.purpose_categories)
        valid_purposes = set(self.indicator_purposes)
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

            # Validate indicator_purposes
            invalid_purposes = [
                p for p in rule.indicator_purposes if p not in valid_purposes
            ]
            if invalid_purposes:
                msg = (
                    f"Rule '{rule.name}' has invalid indicator_purposes: "
                    f"{invalid_purposes}. Valid: {valid_purposes}"
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


class GDPRComplianceClassificationRuleset(
    YAMLRuleset[GDPRComplianceClassificationRule]
):
    """GDPR compliance classification ruleset.

    Provides classification mappings for indicator findings,
    enriching generic findings with GDPR-specific information.
    """

    ruleset_name: ClassVar[str] = "gdpr_compliance_classification"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[GDPRComplianceClassificationRulesetData]
    ] = GDPRComplianceClassificationRulesetData
