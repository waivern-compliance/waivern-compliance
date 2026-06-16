"""Foundational data shapes for LLM validation verdicts.

Defines the structured contract for a single LLM judgement on a finding and
the list-wrapper used to parse batched structured output from the LLM. These
are pure Pydantic data carriers with no behaviour beyond field declarations
and validation.

Lives in waivern-core so that the LLM dispatch layer (``waivern-llm``), the
schema layer (``waivern-schemas``) and the validation orchestration layer
(``waivern-analysers-shared``) can all reference the same verdict shape
without inverting the dependency graph.
"""

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "LLMValidationResponseModel",
    "LLMValidationResultModel",
    "RecommendedActionType",
    "ValidationResultType",
]


ValidationResultType = Literal["TRUE_POSITIVE", "FALSE_POSITIVE"]
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
        default="TRUE_POSITIVE", description="The validation result"
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence score from LLM (0.0-1.0)",
    )
    reasoning: str = Field(
        default="No reasoning provided", description="Reasoning provided by LLM"
    )
    recommended_action: RecommendedActionType = Field(
        default="keep", description="Recommended action from LLM"
    )


class LLMValidationResponseModel(BaseModel):
    """Wrapper model for structured output from LLM validation.

    This model wraps the list of validation results in a single field,
    which is required for LangChain's with_structured_output() method.
    """

    results: list[LLMValidationResultModel] = Field(
        description="List of validation results for each finding"
    )
