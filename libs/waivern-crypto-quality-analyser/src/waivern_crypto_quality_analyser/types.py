"""Configuration types for crypto quality analyser."""

from typing import Any, Self, override

from pydantic import Field
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core import BaseComponentConfiguration
from waivern_core.config_validation import validate_or_raise
from waivern_core.errors import ProcessorConfigError


class CryptoQualityAnalyserConfig(BaseComponentConfiguration):
    """Configuration for CryptoQualityAnalyser.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - Strict validation (no extra fields)

    No LLM validation config — crypto quality assessment is deterministic.
    An algorithm's cryptographic strength is a known property that does not
    require LLM false-positive filtering.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(
            ruleset="local/crypto_quality_indicator/1.0.0"
        ),
        description="Pattern matching configuration for crypto algorithm detection",
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
