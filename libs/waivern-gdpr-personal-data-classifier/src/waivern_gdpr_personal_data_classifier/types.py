"""Configuration types for GDPR personal data classifier."""

from pydantic import Field
from waivern_core import BaseComponentConfiguration


class GDPRPersonalDataClassifierConfig(BaseComponentConfiguration):
    """Configuration for GDPRPersonalDataClassifier.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    ruleset: str = Field(
        default="local/gdpr_personal_data_classification/1.0.0",
        description="Ruleset URI for GDPR personal data classification rules",
    )
