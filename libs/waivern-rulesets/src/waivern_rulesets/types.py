"""Shared types for waivern-rulesets.

This module defines shared rule types used across multiple rulesets,
particularly base classes for framework-specific classification rules.
"""

from typing import Literal

from pydantic import Field
from waivern_core import ClassificationRule


class GDPRClassificationRule(ClassificationRule):
    """Base class for GDPR-specific classification rules.

    Provides common fields used across GDPR classification rulesets:
    - gdpr_data_type: GDPR data type classification
    - special_category: Whether Article 9 special category data
    - article_references: Relevant GDPR articles

    Used by:
    - GDPRPersonalDataClassificationRule (personal data classification)
    - Future GDPR-related classification rulesets
    """

    gdpr_data_type: str = Field(
        min_length=1,
        description="GDPR data type classification (e.g., 'health_data', 'genetic_data')",
    )
    special_category: bool = Field(
        default=False,
        description="Whether this is GDPR Article 9 special category data",
    )
    article_references: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Relevant GDPR article references (e.g., 'Article 9(1)', 'Article 4(1)')",
    )
    lawful_bases: tuple[
        Literal[
            "consent",
            "contract",
            "legal_obligation",
            "vital_interests",
            "public_task",
            "legitimate_interests",
        ],
        ...,
    ] = Field(
        default_factory=tuple,
        description="Applicable GDPR Article 6 lawful bases for processing",
    )


__all__ = ["GDPRClassificationRule"]
