"""Shared models and constants for LLM validation."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

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


class LLMValidationResponseModel(BaseModel):
    """Wrapper model for structured output from LLM validation.

    This model wraps the list of validation results in a single field,
    which is required for LangChain's with_structured_output() method.
    """

    results: list[LLMValidationResultModel] = Field(
        description="List of validation results for each finding"
    )


# Skip reasons and skipped finding type (used by both strategy and orchestrator)


@dataclass
class SkippedFinding[T]:
    """A finding that was skipped during LLM validation.

    Type parameter T is the finding type.
    """

    finding: T
    """The finding that was skipped."""

    reason: str
    """Why validation was skipped (e.g., 'oversized_source', 'missing_content')."""


# Standard skip reasons
SKIP_REASON_OVERSIZED = "oversized_source"
SKIP_REASON_MISSING_CONTENT = "missing_content"
SKIP_REASON_BATCH_ERROR = "batch_error"


# Orchestration result types


@dataclass
class RemovedGroup:
    """A group removed because all samples were false positives.

    Used in validation summaries to report which groups were removed
    and flag them for human review.
    """

    concern_key: str
    """The grouping attribute name (e.g., 'purpose', 'data_category')."""

    concern_value: str
    """The group value that was removed (e.g., 'Documentation Example')."""

    findings_count: int
    """Total findings in this group before removal."""

    samples_validated: int
    """How many samples were validated from this group."""

    reason: str
    """Why the group was removed."""

    require_review: bool
    """Flag indicating this removal should be reviewed by a human."""


@dataclass
class ValidationResult[T]:
    """Result of validation orchestration.

    Contains the kept findings, removed items, and metadata about
    the validation process.

    Type parameter T is the finding type.
    """

    kept_findings: list[T]
    """Findings kept in output.

    Includes:
    - Sampled findings that passed LLM validation (TRUE_POSITIVE or not flagged)
    - Non-sampled findings from groups that weren't removed (kept by inference)
    - Skipped findings (conservative: kept but not validated)
    """

    removed_findings: list[T]
    """Individual findings removed (present in all modes)."""

    removed_groups: list[RemovedGroup]
    """Groups removed (only populated when grouping is enabled)."""

    samples_validated: int
    """Total number of samples sent to LLM for validation."""

    all_succeeded: bool
    """Whether all LLM calls completed without errors."""

    skipped_samples: list[SkippedFinding[T]]
    """Samples that couldn't be validated, with reasons.

    Enables caller to perform fallback validation or report on validation gaps.
    """


# Strategy-level result types


@dataclass
class LLMValidationOutcome[T]:
    """Result of LLM validation strategy with full transparency.

    Provides detailed breakdown of what happened to each finding during
    validation, enabling callers to make informed decisions about fallback
    handling and reporting.

    Type parameter T is the finding type.
    """

    llm_validated_kept: list[T]
    """Findings LLM saw and marked as TRUE_POSITIVE."""

    llm_validated_removed: list[T]
    """Findings LLM saw and marked as FALSE_POSITIVE."""

    llm_not_flagged: list[T]
    """Findings LLM saw but didn't mention (kept via fail-safe)."""

    skipped: list[SkippedFinding[T]]
    """Findings that couldn't be validated (with reasons)."""

    @property
    def kept_findings(self) -> list[T]:
        """All findings to include in output (validated + skipped)."""
        return (
            self.llm_validated_kept
            + self.llm_not_flagged
            + [s.finding for s in self.skipped]
        )

    @property
    def all_findings_validated(self) -> bool:
        """Whether all findings went through LLM validation."""
        return len(self.skipped) == 0

    @property
    def validation_succeeded(self) -> bool:
        """Whether validation completed without errors.

        Note: This is True even if some findings were removed as FALSE_POSITIVE.
        It only returns False if there were skipped findings or errors.
        """
        return self.all_findings_validated

    def with_marked_findings(
        self,
        marker: Callable[[T], T],
    ) -> "LLMValidationOutcome[T]":
        """Return new outcome with validated findings marked.

        Marks both llm_validated_kept and llm_not_flagged since both went
        through LLM validation without being flagged as FALSE_POSITIVE.
        Skipped findings are NOT marked (never went through LLM).

        Args:
            marker: Function that takes a finding and returns a marked copy.

        Returns:
            New LLMValidationOutcome with marked validated findings.

        """
        return LLMValidationOutcome(
            llm_validated_kept=[marker(f) for f in self.llm_validated_kept],
            llm_validated_removed=self.llm_validated_removed,
            llm_not_flagged=[marker(f) for f in self.llm_not_flagged],
            skipped=self.skipped,
        )
