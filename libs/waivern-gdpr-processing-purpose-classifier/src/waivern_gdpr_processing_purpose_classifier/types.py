"""Configuration types for GDPR processing purpose classifier."""

from pydantic import Field
from waivern_core import BaseComponentConfiguration


class GDPRProcessingPurposeClassifierConfig(BaseComponentConfiguration):
    """Configuration for GDPRProcessingPurposeClassifier.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    ruleset: str = Field(
        default="local/gdpr_processing_purpose_classification/1.0.0",
        description="Ruleset URI for GDPR processing purpose classification rules",
    )
