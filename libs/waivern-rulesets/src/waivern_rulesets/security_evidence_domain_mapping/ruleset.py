"""Security evidence domain mapping ruleset.

This ruleset maps processing purpose slugs and personal data indicator
categories to security evidence domains, enabling framework-agnostic
normalisation of indicator findings into structured security evidence items.

Dependencies (keep in sync when upstream rulesets change):
- processing_purposes/1.0.0  → purpose_slugs master list and purpose rules
- personal_data_indicator/1.0.0 → indicator_categories master list and category rules
- SecurityDomain enum in waivern-core → security_domains master list

Tests enforce completeness: test_all_purpose_slugs_are_covered and
test_all_categories_are_covered will fail if the upstream rulesets diverge.
"""

from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator
from waivern_core import ClassificationRule, RulesetData, SecurityDomain

from waivern_rulesets.core.base import YAMLRuleset


class SecurityEvidenceDomainMappingRule(ClassificationRule):
    """Rule mapping indicator values to a security domain.

    Maps indicator values from any supported schema to a primary security domain,
    with an optional secondary domain for indicators that span multiple security
    concerns (e.g., sensitive personal data relates to both data_protection and
    people_controls).

    source_type controls which indicator schema's values are matched:
    - "purpose": matches processing_purpose_indicator.purpose slugs
    - "category": matches personal_data_indicator.category values
    - "algorithm": matches crypto_quality_indicator.algorithm identifiers
    - "service_category": matches service_integration_indicator.service_category slugs
    - "collection_type": matches data_collection_indicator.collection_type slugs
    """

    source_type: Literal[
        "purpose", "category", "algorithm", "service_category", "collection_type"
    ] = Field(
        description="Indicator schema to match",
    )
    indicator_values: tuple[str, ...] = Field(
        min_length=1,
        description="Indicator values (purpose slugs or categories) that map to this domain",
    )
    security_domain: SecurityDomain = Field(
        description="Primary security domain for this mapping",
    )
    secondary_domain: SecurityDomain | None = Field(
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
    """Security evidence domain mapping ruleset data with validation.

    security_domain and secondary_domain are validated by Pydantic as SecurityDomain
    enum fields on the rule model. indicator_values are still cross-validated here
    against the upstream master lists because they have no typed enum equivalent.
    """

    purpose_slugs: list[str] = Field(
        min_length=1,
        description="Master list of valid processing purpose slugs",
    )
    indicator_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid personal data indicator categories",
    )
    algorithm_values: list[str] = Field(
        min_length=1,
        description="Master list of valid cryptographic algorithm identifiers",
    )
    service_category_values: list[str] = Field(
        min_length=1,
        description="Master list of valid service integration category slugs",
    )
    collection_type_values: list[str] = Field(
        min_length=1,
        description="Master list of valid data collection type slugs",
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "SecurityEvidenceDomainMappingRulesetData":
        """Validate all rule indicator_values against upstream master lists."""
        valid_purposes = set(self.purpose_slugs)
        valid_categories = set(self.indicator_categories)
        valid_algorithms = set(self.algorithm_values)
        valid_service_categories = set(self.service_category_values)
        valid_collection_types = set(self.collection_type_values)

        for rule in self.rules:
            match rule.source_type:
                case "purpose":
                    valid_values = valid_purposes
                    label = "purpose"
                case "category":
                    valid_values = valid_categories
                    label = "category"
                case "algorithm":
                    valid_values = valid_algorithms
                    label = "algorithm"
                case "service_category":
                    valid_values = valid_service_categories
                    label = "service_category"
                case "collection_type":
                    valid_values = valid_collection_types
                    label = "collection_type"

            invalid_values = [v for v in rule.indicator_values if v not in valid_values]
            if invalid_values:
                msg = (
                    f"Rule '{rule.name}' has invalid {label} indicator_values: "
                    f"{invalid_values}. Valid: {valid_values}"
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
