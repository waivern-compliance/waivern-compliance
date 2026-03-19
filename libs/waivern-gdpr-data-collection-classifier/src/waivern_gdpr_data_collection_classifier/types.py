"""Configuration types for GDPR data collection classifier."""

from pydantic import Field
from waivern_core import BaseComponentConfiguration


class GDPRDataCollectionClassifierConfig(BaseComponentConfiguration):
    """Configuration for GDPRDataCollectionClassifier.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    ruleset: str = Field(
        default="local/gdpr_data_collection_classification/1.0.0",
        description="Ruleset URI for GDPR data collection classification rules",
    )
