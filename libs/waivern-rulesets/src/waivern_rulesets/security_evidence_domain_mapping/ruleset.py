"""Security evidence domain mapping ruleset.

This ruleset maps processing purpose slugs and personal data indicator
categories to security evidence domains, enabling framework-agnostic
normalisation of indicator findings into structured security evidence items.

Dependencies (keep in sync when upstream rulesets change):
- processing_purposes/1.0.0  → purpose_slugs master list and purpose rules
- personal_data_indicator/1.0.0 → indicator_categories master list and category rules
- SecurityDomain enum in waivern-security-evidence → security_domains master list

Tests enforce completeness: test_all_purpose_slugs_are_covered and
test_all_categories_are_covered will fail if the upstream rulesets diverge.
"""

from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator
from waivern_core import ClassificationRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class SecurityEvidenceDomainMappingRule(ClassificationRule):
    """Rule mapping indicator values to a security domain.

    Maps either processing purpose slugs or personal data indicator categories
    to a primary security domain, with an optional secondary domain for
    indicators that span multiple security concerns (e.g., sensitive personal
    data relates to both data_protection and people_controls).

    source_type controls which indicator schema's values are matched:
    - "purpose": matches processing_purpose_indicator.purpose slugs
    - "category": matches personal_data_indicator.category values
    """

    source_type: Literal["purpose", "category"] = Field(
        description="Indicator schema to match: 'purpose' or 'category'",
    )
    indicator_values: tuple[str, ...] = Field(
        min_length=1,
        description="Indicator values (purpose slugs or categories) that map to this domain",
    )
    security_domain: str = Field(
        min_length=1,
        description="Primary security domain for this mapping (snake_case)",
    )
    secondary_domain: str | None = Field(
        default=None,
        description="Optional secondary domain when evidence spans multiple security areas",
    )

    @field_validator("indicator_values", mode="before")
    @classmethod
    def convert_list_to_tuple(cls, v: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v


class SecurityEvidenceDomainMappingRulesetData(
    RulesetData[SecurityEvidenceDomainMappingRule]
):
    """Security evidence domain mapping ruleset data with validation."""

    security_domains: list[str] = Field(
        min_length=1,
        description="Master list of valid security domain values",
    )
    purpose_slugs: list[str] = Field(
        min_length=1,
        description="Master list of valid processing purpose slugs",
    )
    indicator_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid personal data indicator categories",
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "SecurityEvidenceDomainMappingRulesetData":
        """Validate all rules against master lists."""
        valid_domains = set(self.security_domains)
        valid_purposes = set(self.purpose_slugs)
        valid_categories = set(self.indicator_categories)

        for rule in self.rules:
            if rule.security_domain not in valid_domains:
                msg = (
                    f"Rule '{rule.name}' has invalid security_domain "
                    f"'{rule.security_domain}'. Valid: {valid_domains}"
                )
                raise ValueError(msg)

            if (
                rule.secondary_domain is not None
                and rule.secondary_domain not in valid_domains
            ):
                msg = (
                    f"Rule '{rule.name}' has invalid secondary_domain "
                    f"'{rule.secondary_domain}'. Valid: {valid_domains}"
                )
                raise ValueError(msg)

            if rule.source_type == "purpose":
                invalid_values = [
                    v for v in rule.indicator_values if v not in valid_purposes
                ]
                if invalid_values:
                    msg = (
                        f"Rule '{rule.name}' has invalid purpose indicator_values: "
                        f"{invalid_values}. Valid: {valid_purposes}"
                    )
                    raise ValueError(msg)
            else:  # "category"
                invalid_values = [
                    v for v in rule.indicator_values if v not in valid_categories
                ]
                if invalid_values:
                    msg = (
                        f"Rule '{rule.name}' has invalid category indicator_values: "
                        f"{invalid_values}. Valid: {valid_categories}"
                    )
                    raise ValueError(msg)

        return self


class SecurityEvidenceDomainMappingRuleset(
    YAMLRuleset[SecurityEvidenceDomainMappingRule]
):
    """Security evidence domain mapping ruleset.

    Maps processing purpose slugs and personal data indicator categories to
    framework-agnostic security domains. Used by SecurityEvidenceNormaliser to
    convert indicator findings into structured security evidence items.
    """

    ruleset_name: ClassVar[str] = "security_evidence_domain_mapping"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[SecurityEvidenceDomainMappingRulesetData]
    ] = SecurityEvidenceDomainMappingRulesetData
