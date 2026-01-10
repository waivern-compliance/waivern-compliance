"""Shared models and constants for LLM validation."""

from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter

# Type alias for validation results
ValidationResultType = Literal["TRUE_POSITIVE", "FALSE_POSITIVE", "UNKNOWN"]

# Type alias for recommended actions
RecommendedActionType = Literal["keep", "discard", "flag_for_review"]


class LLMValidationResultModel(BaseModel):
    """Strongly typed model for LLM validation results.

    This model represents a single validation result from the LLM, including
    the finding ID for explicit matching back to the original finding.
    Using UUIDs instead of indices makes matching robust against LLM reordering.
    """

    finding_id: str = Field(
        min_length=1,
        description="UUID of the finding this result corresponds to (echo back exactly)",
    )
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


# TypeAdapter for validating a list of validation results from LLM response
LLMValidationResultListAdapter = TypeAdapter(list[LLMValidationResultModel])
