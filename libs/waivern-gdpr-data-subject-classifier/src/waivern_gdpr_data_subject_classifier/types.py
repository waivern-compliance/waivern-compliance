"""Configuration types for GDPR data subject classifier."""

from pydantic import Field
from waivern_core import BaseComponentConfiguration


class GDPRDataSubjectClassifierConfig(BaseComponentConfiguration):
    """Configuration for GDPRDataSubjectClassifier.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    ruleset: str = Field(
        default="local/gdpr_data_subject_classification/1.0.0",
        description="Ruleset URI for GDPR data subject classification rules",
    )
