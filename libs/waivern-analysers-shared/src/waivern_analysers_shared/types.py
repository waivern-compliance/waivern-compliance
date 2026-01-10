"""Configuration types for analysers."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LLMBatchingStrategy(str, Enum):
    """Batching strategy for LLM validation.

    BATCH_FINDINGS: Current approach - batch by finding count (default)
    BATCH_FILES: New approach - batch by file, send full content
    """

    BATCH_FINDINGS = "batch_findings"
    BATCH_FILES = "batch_files"


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
        default=True,
        description="Whether to enable LLM-based validation to filter false positives",
    )

    llm_batch_size: int = Field(
        default=50, ge=1, le=200, description="Batch size for LLM processing"
    )

    llm_validation_mode: Literal["standard", "conservative", "aggressive"] = Field(
        default="standard", description="LLM validation mode"
    )

    llm_batching_strategy: LLMBatchingStrategy = Field(
        default=LLMBatchingStrategy.BATCH_FINDINGS,
        description="Strategy for batching findings: 'batch_findings' (default) or 'batch_files'",
    )

    batching: BatchingConfig = Field(
        default_factory=BatchingConfig,
        description="Token-aware batching configuration (used when strategy is 'batch_files')",
    )
