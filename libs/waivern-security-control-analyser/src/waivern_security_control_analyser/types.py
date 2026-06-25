"""Configuration types for security control analyser."""

from typing import Any, Self, override

from pydantic import Field
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core import BaseComponentConfiguration
from waivern_core.config_validation import validate_or_raise
from waivern_core.errors import ProcessorConfigError


class SecurityControlAnalyserConfig(BaseComponentConfiguration):
    """Configuration for SecurityControlAnalyser.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
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
