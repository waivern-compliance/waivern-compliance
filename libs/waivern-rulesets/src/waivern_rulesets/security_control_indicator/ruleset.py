"""Security control indicator ruleset.

This module defines a ruleset for detecting security control implementations
in source code and evaluating their quality (positive or negative polarity).

Unlike the processing_purpose_indicator path (which detects presence with
neutral polarity), every pattern here has a definitive quality signal:
a prepared_statement() call is positive evidence; an eval() of user input
is negative evidence. No neutral polarity is permitted.
"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class SecurityControlIndicatorRule(DetectionRule):
    """Security control indicator detection rule.

    Extends DetectionRule with fields that drive direct SecurityEvidenceModel
    construction in SecurityControlAnalyser — no domain mapping lookup needed
    at runtime because the domain and polarity live on the rule itself.
    """

    security_domain: str = Field(
        description="Security domain this control belongs to (snake_case)"
    )
    polarity: Literal["positive", "negative"] = Field(
        description=(
            "Evidence polarity: positive (good practice) or negative (bad practice). "
            "Neutral is not permitted — if a pattern cannot be classified, "
            "it belongs in the processing_purpose ruleset, not here."
        )
    )


class SecurityControlIndicatorRulesetData(RulesetData[SecurityControlIndicatorRule]):
    """Security control indicator ruleset data with domain validation.

    Validates that every rule's security_domain is drawn from the master list.
    This keeps waivern-rulesets independent of waivern-security-evidence while
    still enforcing the shared SecurityDomain taxonomy at parse time.
    """

    security_domains: list[str] = Field(
        min_length=1,
        description="Master list of valid security domain values",
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "SecurityControlIndicatorRulesetData":
        """Validate all rules against the security_domains master list."""
        valid_domains = set(self.security_domains)
        for rule in self.rules:
            if rule.security_domain not in valid_domains:
                msg = (
                    f"Rule '{rule.name}' has invalid security_domain "
                    f"'{rule.security_domain}'. Valid: {valid_domains}"
                )
                raise ValueError(msg)
        return self


class SecurityControlIndicatorRuleset(YAMLRuleset[SecurityControlIndicatorRule]):
    """Security control indicator detection ruleset.

    Detects security control implementations directly in source code and assigns
    a binary polarity (positive/negative) and a security domain to each match.

    Named 'security_control_indicator' rather than 'security_evidence' because:
    - 'security_evidence' would be ambiguous with the output schema name
    - Multiple rulesets may produce security_evidence (this one for code controls;
      future ones for network config, IaC, etc.)
    - The name scopes it precisely to source-code security control detection
    """

    ruleset_name: ClassVar[str] = "security_control_indicator"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[SecurityControlIndicatorRulesetData]
    ] = SecurityControlIndicatorRulesetData
