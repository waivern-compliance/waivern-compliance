"""Types for LLM-based validation configuration."""

from typing import Literal

from pydantic import BaseModel, Field


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

    sampling_size: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Number of samples per group for sampling-based validation. "
        "Defaults to 3 to limit LLM API costs.",
    )
