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
    - privacy_category: Privacy category for reporting/governance (from legal team)
    - special_category: Whether Article 9 special category data (core GDPR concern)
    - article_references: Relevant GDPR articles

    Note: privacy_category values like 'identification_data', 'financial_data' are
    NOT GDPR-defined terms - they're from legal team for reporting purposes.
    GDPR only mandates: personal data (Article 4) vs special category (Article 9).

    Used by:
    - GDPRPersonalDataClassificationRule (personal data classification)
    - Future GDPR-related classification rulesets
    """

    privacy_category: str = Field(
        min_length=1,
        description="Privacy category for reporting (e.g., 'identification_data', 'health_data')",
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
