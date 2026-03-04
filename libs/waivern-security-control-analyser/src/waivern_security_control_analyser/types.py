"""Configuration types for security control analyser."""

from pydantic import Field
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core import BaseComponentConfiguration


class SecurityControlAnalyserConfig(BaseComponentConfiguration):
    """Configuration for SecurityControlAnalyser.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)

    No LLM validation config — security control detection is deterministic.
    Domain and polarity are carried directly on each rule; no mapping lookup
    or probabilistic assessment is required.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(
            ruleset="local/security_control_indicator/1.0.0"
        ),
        description="Pattern matching configuration for security control detection",
    )

    # from_properties() inherited from BaseComponentConfiguration
