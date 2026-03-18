"""Shared types for waivern-rulesets.

This module defines shared rule types used across multiple rulesets,
particularly base classes for framework-specific classification rules.
"""

from pydantic import Field
from waivern_core import ClassificationRule


class GDPRClassificationRule(ClassificationRule):
    """Base class for GDPR-specific classification rules.

    Provides the common field used across all GDPR classification rulesets:
    - article_references: Relevant GDPR articles

    Used by:
    - GDPRPersonalDataClassificationRule (personal data classification)
    - GDPRDataSubjectClassificationRule (data subject classification)
    - GDPRProcessingPurposeClassificationRule (processing purpose classification)
    """

    article_references: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Relevant GDPR article references (e.g., 'Article 9(1)', 'Article 4(1)')",
    )


__all__ = ["GDPRClassificationRule"]
