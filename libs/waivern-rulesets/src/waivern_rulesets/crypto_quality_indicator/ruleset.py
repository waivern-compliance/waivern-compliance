"""Crypto quality indicator ruleset.

This module defines a ruleset for detecting cryptographic algorithm usage
and evaluating implementation quality (strong, weak, or deprecated).

Unlike personal data detection, quality assessment is deterministic:
an algorithm's cryptographic strength is a known property, not a context-
dependent judgement. No LLM validation is required.
"""

from typing import ClassVar, Literal

from pydantic import Field
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class CryptoQualityIndicatorRule(DetectionRule):
    """Crypto quality indicator detection rule.

    Extends DetectionRule with cryptography-specific fields that drive
    polarity assignment in the analyser's pattern matcher.
    """

    algorithm: str = Field(
        description="Canonical algorithm name (e.g., 'md5', 'bcrypt')"
    )
    quality_rating: Literal["strong", "weak", "deprecated"] = Field(
        description="Cryptographic quality rating of the algorithm"
    )


class CryptoQualityIndicatorRulesetData(RulesetData[CryptoQualityIndicatorRule]):
    """Crypto quality indicator ruleset data structure.

    quality_rating validation is handled by the Literal type on
    CryptoQualityIndicatorRule — no separate master list is needed.
    """

    pass


class CryptoQualityIndicatorRuleset(YAMLRuleset[CryptoQualityIndicatorRule]):
    """Crypto quality indicator detection ruleset.

    Provides structured access to cryptographic algorithm patterns for
    security evidence analysis.
    """

    ruleset_name: ClassVar[str] = "crypto_quality_indicator"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[CryptoQualityIndicatorRulesetData]
    ] = CryptoQualityIndicatorRulesetData
