"""Protocol definitions for waivern-rulesets.

This module defines protocols (structural subtyping) for rulesets that
require extended interfaces beyond the base AbstractRuleset.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from waivern_rulesets.gdpr_data_subject_classification import (
        GDPRDataSubjectClassificationRule,
        RiskModifiers,
    )


class DataSubjectClassificationRulesetProtocol(Protocol):
    """Contract for data subject classification rulesets.

    This protocol extends beyond AbstractRuleset to include risk modifier access.
    Implementations must provide both category mapping rules and risk modifier
    patterns for complete GDPR data subject classification.

    The built-in GDPRDataSubjectClassificationRuleset implements this protocol.
    Users can provide custom implementations for alternative classification schemes.
    """

    @property
    def name(self) -> str:
        """Get the canonical name of this ruleset."""
        ...

    @property
    def version(self) -> str:
        """Get the version of this ruleset."""
        ...

    def get_rules(self) -> "tuple[GDPRDataSubjectClassificationRule, ...]":
        """Get the classification rules.

        Returns:
            Immutable tuple of classification rules mapping indicator
            categories to GDPR data subject categories.

        """
        ...

    def get_risk_modifiers(self) -> "RiskModifiers":
        """Get the risk modifiers for data subject classification.

        Returns:
            Risk modifiers containing patterns for detecting minors,
            vulnerable individuals, and other risk-relevant contexts.

        """
        ...


__all__ = ["DataSubjectClassificationRulesetProtocol"]
