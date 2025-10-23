"""Configuration types for personal data analysis analyser."""

from typing import Any, Self

from pydantic import BaseModel, Field
from waivern_analysers_shared.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)


class PersonalDataAnalyserConfig(BaseModel):
    """Configuration for PersonalDataAnalyser with nested runner configs.

    This provides clear separation of concerns where each runner has its own
    configuration section in the runbook properties.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(ruleset="personal_data"),
        description="Pattern matching configuration for personal data detection",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=lambda: LLMValidationConfig(enable_llm_validation=True),
        description="LLM validation configuration for filtering false positives",
    )

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties with nested structure.

        Args:
            properties: Raw properties from runbook with nested configuration

        Returns:
            Validated configuration object

        """
        return cls.model_validate(properties)
