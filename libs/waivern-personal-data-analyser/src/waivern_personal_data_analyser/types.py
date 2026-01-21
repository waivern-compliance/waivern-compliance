"""Configuration types for personal data analysis analyser."""

from pydantic import Field
from waivern_analysers_shared.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_core import BaseComponentConfiguration


class PersonalDataAnalyserConfig(BaseComponentConfiguration):
    """Configuration for PersonalDataAnalyser with DI support.

    This provides clear separation of concerns where each runner has its own
    configuration section in the runbook properties.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(
            ruleset="local/personal_data_indicator/1.0.0"
        ),
        description="Pattern matching configuration for personal data detection",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=LLMValidationConfig,
        description="LLM validation configuration for filtering false positives",
    )

    # from_properties() inherited from BaseComponentConfiguration
