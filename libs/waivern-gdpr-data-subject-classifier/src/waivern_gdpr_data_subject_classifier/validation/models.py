"""Response models for risk modifier LLM validation."""

from pydantic import BaseModel, Field


class RiskModifierResultModel(BaseModel):
    """Strongly typed model for risk modifier validation results.

    This model represents a single validation result from the LLM, including
    the finding ID for explicit matching back to the original finding.
    """

    finding_id: str = Field(
        min_length=1,
        description="UUID of the finding this result corresponds to (echo back exactly)",
    )
    risk_modifiers: list[str] = Field(
        description="List of detected risk modifier names (e.g., ['minor', 'vulnerable_individual'])",
    )
    reasoning: str = Field(
        default="No risk modifiers detected",
        description="Explanation for audit trail",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score from LLM (0.0-1.0)",
    )


class RiskModifierValidationResponseModel(BaseModel):
    """Wrapper model for structured output from LLM risk modifier validation.

    This model wraps the list of validation results in a single field,
    which is required for LangChain's with_structured_output() method.
    """

    results: list[RiskModifierResultModel] = Field(
        description="List of validation results for each finding",
    )
