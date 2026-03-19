"""Configuration types for GDPR service integration classifier."""

from pydantic import Field
from waivern_core import BaseComponentConfiguration


class GDPRServiceIntegrationClassifierConfig(BaseComponentConfiguration):
    """Configuration for GDPRServiceIntegrationClassifier.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    ruleset: str = Field(
        default="local/gdpr_service_integration_classification/1.0.0",
        description="Ruleset URI for GDPR service integration classification rules",
    )
