"""Security control indicator ruleset.

This module defines a ruleset for detecting security control implementations
in source code and evaluating their quality (positive or negative polarity).

Unlike the processing_purpose_indicator path (which detects presence with
neutral polarity), every pattern here has a definitive quality signal:
a prepared_statement() call is positive evidence; an eval() of user input
is negative evidence. No neutral polarity is permitted.
"""

from typing import ClassVar, Literal

from pydantic import Field
from waivern_core import DetectionRule, RulesetData
from waivern_schemas.security_domain import SecurityDomain

from waivern_rulesets.core.base import YAMLRuleset


class SecurityControlIndicatorRule(DetectionRule):
    """Security control indicator detection rule.

    Extends DetectionRule with fields that drive direct SecurityEvidenceModel
    construction in SecurityControlAnalyser — no domain mapping lookup needed
    at runtime because the domain and polarity live on the rule itself.
    """

    security_domain: SecurityDomain = Field(
        description="Security domain this control belongs to"
    )
    polarity: Literal["positive", "negative"] = Field(
        description=(
            "Evidence polarity: positive (good practice) or negative (bad practice). "
            "Neutral is not permitted — if a pattern cannot be classified, "
            "it belongs in the processing_purpose ruleset, not here."
        )
    )


class SecurityControlIndicatorRulesetData(RulesetData[SecurityControlIndicatorRule]):
    """Security control indicator ruleset data.

    security_domain values are validated by Pydantic against the SecurityDomain
    enum at rule parse time — no manual cross-field validator needed.
    """

    pass


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
