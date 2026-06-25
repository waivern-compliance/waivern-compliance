"""Configuration types for GDPR data collection classifier."""

from typing import Any, Self, override

from pydantic import Field
from waivern_core import BaseComponentConfiguration
from waivern_core.config_validation import validate_or_raise
from waivern_core.errors import ProcessorConfigError


class GDPRDataCollectionClassifierConfig(BaseComponentConfiguration):
    """Configuration for GDPRDataCollectionClassifier.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen)
    - Strict validation (no extra fields)
    """

    ruleset: str = Field(
        default="local/gdpr_data_collection_classification/1.0.0",
        description="Ruleset URI for GDPR data collection classification rules",
    )

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties.

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Validated configuration object

        Raises:
            ProcessorConfigError: If validation fails

        """
        return validate_or_raise(cls, properties, ProcessorConfigError)
