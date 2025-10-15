"""Shared models and constants for LLM validation."""

from typing import Literal

from pydantic import BaseModel, Field

# Type alias for validation results
ValidationResultType = Literal["TRUE_POSITIVE", "FALSE_POSITIVE", "UNKNOWN"]

# Type alias for recommended actions
RecommendedActionType = Literal["keep", "discard", "flag_for_review"]


class LLMValidationResultModel(BaseModel):
    """Strongly typed model for LLM validation results.

    This model was extracted from both Personal Data and Processing Purpose
    analysers to eliminate code duplication and ensure consistency.
    """

    validation_result: ValidationResultType = Field(
        default="UNKNOWN", description="The validation result"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score from LLM",
    )
    reasoning: str = Field(
        default="No reasoning provided", description="Reasoning provided by LLM"
    )
    recommended_action: RecommendedActionType = Field(
        default="keep", description="Recommended action from LLM"
    )
