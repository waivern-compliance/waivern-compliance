"""GDPR data collection classification ruleset.

This module defines a ruleset for classifying data collection indicators
according to GDPR requirements. It maps collection type slugs to GDPR-specific
purpose categories and article references.
"""

from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator
from waivern_core import RulesetData

from waivern_rulesets.core.base import YAMLRuleset
from waivern_rulesets.types import GDPRClassificationRule


class GDPRDataCollectionClassificationRule(GDPRClassificationRule):
    """GDPR data collection classification rule.

    Maps data collection indicator types to GDPR-specific classifications.
    Unlike detection rules, these rules don't have patterns - they map from
    collection type slugs to GDPR purpose categories.
    """

    purpose_category: str = Field(
        description="GDPR purpose category for reporting (e.g., 'context_dependent')",
    )
    indicator_collection_types: tuple[str, ...] = Field(
        min_length=1,
        description="Collection type slugs this rule classifies (from indicator)",
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
        "indicator_collection_types",
        "typical_lawful_bases",
        mode="before",
    )
    @classmethod
    def convert_list_to_tuple(cls, v: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v


class GDPRDataCollectionClassificationRulesetData(
    RulesetData[GDPRDataCollectionClassificationRule]
):
    """GDPR data collection classification ruleset data with validation."""

    # Master list of valid purpose categories (for reporting/governance)
    purpose_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid GDPR purpose categories",
    )

    # Valid collection type slugs that can be mapped
    indicator_collection_types: list[str] = Field(
        min_length=1,
        description="Master list of valid collection type slugs from indicator",
    )

    # Sensitive categories subset
    sensitive_categories: list[str] = Field(
        default_factory=list,
        description="Subset of purpose_categories considered privacy-sensitive",
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "GDPRDataCollectionClassificationRulesetData":
        """Validate all rules against master lists."""
        valid_cats = set(self.purpose_categories)
        valid_collection_types = set(self.indicator_collection_types)
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

            # Validate indicator_collection_types
            invalid_types = [
                ct
                for ct in rule.indicator_collection_types
                if ct not in valid_collection_types
            ]
            if invalid_types:
                msg = (
                    f"Rule '{rule.name}' has invalid indicator_collection_types: "
                    f"{invalid_types}. Valid: {valid_collection_types}"
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


class GDPRDataCollectionClassificationRuleset(
    YAMLRuleset[GDPRDataCollectionClassificationRule]
):
    """GDPR data collection classification ruleset.

    Provides classification mappings for data collection indicators,
    enriching findings with GDPR-specific information.
    """

    ruleset_name: ClassVar[str] = "gdpr_data_collection_classification"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[GDPRDataCollectionClassificationRulesetData]
    ] = GDPRDataCollectionClassificationRulesetData
