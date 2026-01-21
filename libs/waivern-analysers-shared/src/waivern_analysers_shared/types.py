"""Configuration types for analysers."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator
from waivern_core.schemas import BaseFindingModel


class PatternType(Enum):
    """Type of pattern matching strategy.

    WORD_BOUNDARY: Matches patterns at word boundaries only, avoiding false
        positives in compound words or encoded strings (e.g., base64).

    REGEX: Full regex matching for detecting actual data values like
        email addresses, phone numbers, etc.
    """

    WORD_BOUNDARY = "word_boundary"
    REGEX = "regex"


@dataclass(frozen=True, slots=True)
class PatternMatch:
    """A single pattern match with position information.

    Immutable value object representing where a pattern matched in content.
    Used to track matches from both word-boundary and regex patterns with
    their exact positions for evidence extraction.

    Attributes:
        pattern: The pattern string that matched
        pattern_type: Whether this was word-boundary or regex matching
        start: Start position (inclusive) in the content
        end: End position (exclusive) in the content

    """

    pattern: str
    pattern_type: PatternType
    start: int
    end: int

    @property
    def matched_text_length(self) -> int:
        """Length of the actual matched text."""
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class PatternMatchResult:
    """Result of searching for a pattern in content.

    Contains the first match position (for evidence extraction) and
    the total match count (for auditing/reporting).

    Attributes:
        pattern: The pattern that was searched for
        first_match: The first match found, or None if no matches
        match_count: Total number of times the pattern matched

    """

    pattern: str
    first_match: PatternMatch | None
    match_count: int


class SchemaReader[T](Protocol):
    """Protocol for schema reader modules.

    Schema readers are modules that transform raw message content into typed
    Pydantic models. Each analyser has reader modules for each supported schema
    version (e.g., schema_readers/standard_input_1_0_0.py).

    This protocol enables type-safe dynamic module loading - analysers can use
    importlib to load readers while maintaining proper type inference.

    Type parameter T is the return type of read() (e.g., StandardInputDataModel).
    """

    def read(self, content: dict[str, Any]) -> T:
        """Transform raw content to typed model.

        Args:
            content: Raw message content dictionary.

        Returns:
            Typed Pydantic model for the schema.

        """
        ...


class SchemaInputHandler[T: BaseFindingModel](Protocol):
    """Protocol for schema-specific input handlers.

    All handlers must implement this interface to ensure consistent
    integration with the analyser. The analyser uses this protocol
    to remain schema-agnostic.

    Type parameter T is the finding model type (must extend BaseFindingModel).
    """

    def analyse(self, data: object) -> list[T]:
        """Analyse input data for patterns.

        Args:
            data: Schema-validated input data from the reader.

        Returns:
            List of findings.

        Raises:
            TypeError: If data is not the expected schema type.

        """
        ...


class BatchingConfig(BaseModel):
    """Configuration for token-aware batching.

    Only exposes model_context_window as configurable.
    Other parameters (output_ratio, safety_buffer, prompt_overhead) are
    constants in token_estimation.py since they're implementation details.
    """

    model_context_window: int | None = Field(
        default=None,
        description="Override context window size in tokens. Auto-detected from model name if None.",
    )


class EvidenceContextSize(str, Enum):
    """Evidence context size options."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    FULL = "full"


class PatternMatchingConfig(BaseModel):
    """Strongly typed configuration for pattern matching analysis."""

    ruleset: str = Field(
        description="Ruleset URI in format provider/name/version (e.g., 'local/personal_data/1.0.0')"
    )

    evidence_context_size: str = Field(
        default="medium", description="Context size for evidence extraction"
    )

    @field_validator("evidence_context_size")
    @classmethod
    def validate_evidence_context_size(cls, v: str) -> str:
        """Validate evidence context size values."""
        allowed = ["small", "medium", "large", "full"]
        if v not in allowed:
            raise ValueError(
                f"evidence_context_size must be one of {allowed}, got: {v}"
            )
        return v

    maximum_evidence_count: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum number of evidence items to collect per finding",
    )


class LLMValidationConfig(BaseModel):
    """Strongly typed configuration for LLM validation analysis."""

    enable_llm_validation: bool = Field(
        default=False,
        description="Whether to enable LLM-based validation to filter false positives",
    )

    llm_batch_size: int = Field(
        default=50, ge=1, le=200, description="Batch size for LLM processing"
    )

    llm_validation_mode: Literal["standard", "conservative", "aggressive"] = Field(
        default="standard", description="LLM validation mode"
    )

    batching: BatchingConfig = Field(
        default_factory=BatchingConfig,
        description="Token-aware batching configuration for extended context validation",
    )

    sampling_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Number of samples per group for sampling-based validation. None = validate all.",
    )
