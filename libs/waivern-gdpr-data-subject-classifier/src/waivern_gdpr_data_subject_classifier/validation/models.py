"""Response models for risk modifier LLM validation."""

from dataclasses import dataclass, field

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


# =============================================================================
# Strategy Result Types (dataclasses)
# =============================================================================


@dataclass
class RiskModifierBatchResult:
    """Result from validating a single batch of findings.

    This is the intermediate per-batch result type (TBatchResult) used by
    the RiskModifierValidationStrategy.
    """

    finding_modifiers: dict[str, list[str]] = field(default_factory=dict)
    """Mapping of finding_id → detected modifiers."""

    finding_confidences: dict[str, float] = field(default_factory=dict)
    """Mapping of finding_id → confidence score."""

    finding_categories: dict[str, str] = field(default_factory=dict)
    """Mapping of finding_id → data_subject_category."""


@dataclass
class CategoryRiskModifierResult:
    """Risk modifiers detected for a single data subject category.

    Represents the aggregated result for one category, combining modifiers
    from all findings in that category.
    """

    category: str
    """Data subject category (e.g., 'patient', 'employee')."""

    detected_modifiers: list[str]
    """Union of all modifiers detected across findings in this category."""

    sample_count: int
    """Number of findings sampled for this category."""

    confidence: float
    """Average confidence across all findings in this category."""


@dataclass
class RiskModifierValidationResult:
    """Complete result of risk modifier validation.

    This is the final result type (TResult) returned by
    RiskModifierValidationStrategy.validate_findings().
    """

    category_results: list[CategoryRiskModifierResult]
    """Risk modifier results grouped by data subject category."""

    total_findings: int
    """Total number of findings received (sampled + failed)."""

    total_sampled: int
    """Number of findings successfully validated by LLM."""

    validation_succeeded: bool
    """False if any batch failed validation."""
