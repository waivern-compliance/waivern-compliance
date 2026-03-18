"""Configuration types for GDPR compliance classifier."""

from pydantic import Field
from waivern_core import BaseComponentConfiguration


class GDPRComplianceClassifierConfig(BaseComponentConfiguration):
    """Configuration for GDPRComplianceClassifier.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    ruleset: str = Field(
        default="local/gdpr_compliance_classification/1.0.0",
        description="Ruleset URI for GDPR compliance classification rules",
    )
