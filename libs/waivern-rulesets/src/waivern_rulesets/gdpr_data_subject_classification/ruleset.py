"""GDPR data subject classification ruleset.

This module defines a ruleset for classifying data subject indicators
according to GDPR requirements. It maps data subject detection categories
to GDPR-specific data subject types and article references.
"""

from typing import ClassVar, cast

from pydantic import BaseModel, Field, field_validator, model_validator
from waivern_core import ClassificationRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class RiskModifier(BaseModel):
    """Risk modifier definition for data subject classification."""

    pattern: str = Field(description="Regex pattern to match risk modifier")
    modifier: str = Field(description="Name of the risk modifier")
    article_references: list[str] = Field(
        min_length=1,
        description="GDPR article references for this modifier",
    )


class RiskModifiers(BaseModel):
    """Risk modifiers container."""

    risk_increasing: list[RiskModifier] = Field(
        default_factory=list,
        description="Modifiers that increase processing risk",
    )
    risk_decreasing: list[RiskModifier] = Field(
        default_factory=list,
        description="Modifiers that decrease processing risk",
    )


class GDPRDataSubjectClassificationRule(ClassificationRule):
    """GDPR data subject classification rule.

    Maps data subject indicator categories to GDPR-specific classifications.
    Unlike detection rules, these rules don't have patterns - they map from
    indicator categories to GDPR data subject types.

    Note: Unlike GDPRClassificationRule (for personal data), data subject
    classification doesn't use privacy_category because it classifies WHO
    the data is about (employee, customer), not WHAT TYPE of data it is.
    """

    data_subject_category: str = Field(
        description="GDPR data subject category for reporting",
    )
    article_references: list[str] = Field(
        default_factory=list,
        description="Relevant GDPR article references",
    )
    typical_lawful_bases: tuple[str, ...] = Field(
        min_length=1,
        description="Typical GDPR Article 6 lawful bases for processing",
    )
    indicator_categories: tuple[str, ...] = Field(
        min_length=1,
        description="Data subject indicator categories this rule classifies",
    )

    @field_validator("indicator_categories", "typical_lawful_bases", mode="before")
    @classmethod
    def convert_list_to_tuple(cls, v: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v


class GDPRDataSubjectClassificationRulesetData(
    RulesetData[GDPRDataSubjectClassificationRule]
):
    """GDPR data subject classification ruleset data with validation."""

    # Default article references
    default_article_references: list[str] = Field(
        min_length=1,
        description="Default GDPR article references for all data subjects",
    )

    # Master list of valid data subject categories (for reporting/governance)
    data_subject_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid data subject categories for reporting",
    )

    # Valid indicator categories that can be mapped
    indicator_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid data subject indicator categories",
    )

    # Risk modifiers
    risk_modifiers: RiskModifiers = Field(
        default_factory=RiskModifiers,
        description="Risk modifiers for data subject processing",
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "GDPRDataSubjectClassificationRulesetData":
        """Validate all rules against master lists."""
        valid_ds_cats = set(self.data_subject_categories)
        valid_indicator_cats = set(self.indicator_categories)

        for rule in self.rules:
            # Validate data_subject_category
            if rule.data_subject_category not in valid_ds_cats:
                msg = (
                    f"Rule '{rule.name}' has invalid data_subject_category "
                    f"'{rule.data_subject_category}'. Valid: {valid_ds_cats}"
                )
                raise ValueError(msg)

            # Validate indicator_categories
            invalid_cats = [
                cat
                for cat in rule.indicator_categories
                if cat not in valid_indicator_cats
            ]
            if invalid_cats:
                msg = (
                    f"Rule '{rule.name}' has invalid indicator_categories: "
                    f"{invalid_cats}. Valid: {valid_indicator_cats}"
                )
                raise ValueError(msg)

        return self


class GDPRDataSubjectClassificationRuleset(
    YAMLRuleset[GDPRDataSubjectClassificationRule]
):
    """GDPR data subject classification ruleset.

    Provides classification mappings for data subject indicators,
    enriching generic findings with GDPR-specific information.
    """

    ruleset_name: ClassVar[str] = "gdpr_data_subject_classification"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[GDPRDataSubjectClassificationRulesetData]
    ] = GDPRDataSubjectClassificationRulesetData

    def get_risk_modifiers(self) -> RiskModifiers:
        """Get the risk modifiers for data subject classification.

        Returns:
            Risk modifiers containing patterns for detecting minors,
            vulnerable individuals, and other risk-relevant contexts.

        """
        data = cast(GDPRDataSubjectClassificationRulesetData, self._load_data())
        return data.risk_modifiers
