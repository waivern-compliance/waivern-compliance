"""Configuration types for data subject analyser."""

from pydantic import Field
from waivern_analysers_shared.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_core import BaseComponentConfiguration


class DataSubjectAnalyserConfig(BaseComponentConfiguration):
    """Configuration for DataSubjectAnalyser.

    Groups related configuration parameters to reduce constructor complexity.
    Uses Pydantic for validation and default values.
    Inherits from BaseComponentConfiguration for DI system integration.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(
            ruleset="local/data_subject_indicator/1.0.0"
        ),
        description="Pattern matching configuration",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=lambda: LLMValidationConfig(enable_llm_validation=False),
        description="LLM validation configuration for improving classification accuracy",
    )
