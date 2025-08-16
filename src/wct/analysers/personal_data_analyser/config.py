"""Strongly typed configuration for PersonalDataAnalyser."""

from typing import Any

from pydantic import BaseModel
from typing_extensions import Self

from wct.analysers.runners.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)


class PersonalDataAnalyserProperties(BaseModel):
    """Strongly typed configuration for PersonalDataAnalyser with nested runner configs.

    This provides clear separation of concerns where each runner has its own
    configuration section in the runbook properties.
    """

    pattern_matching: PatternMatchingConfig = PatternMatchingConfig()
    llm_validation: LLMValidationConfig = LLMValidationConfig()

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties with nested structure.

        Args:
            properties: Raw properties from runbook with nested configuration

        Returns:
            Validated configuration object

        """
        return cls.model_validate(properties)
