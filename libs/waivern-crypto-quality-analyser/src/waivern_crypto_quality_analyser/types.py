"""Configuration types for crypto quality analyser."""

from pydantic import Field
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core import BaseComponentConfiguration


class CryptoQualityAnalyserConfig(BaseComponentConfiguration):
    """Configuration for CryptoQualityAnalyser.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - from_properties() factory method (inherited)
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

    # from_properties() inherited from BaseComponentConfiguration
