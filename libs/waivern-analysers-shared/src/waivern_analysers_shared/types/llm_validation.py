"""Types for LLM-based validation configuration."""

from typing import Literal

from pydantic import BaseModel, Field


# TODO: Post-migration cleanup (once all processors use LLMService v2):
#   Review whether BatchingConfig is still needed. LLMService v2 handles
#   batching internally and doesn't use this config. Consider removing
#   or moving to LLMServiceConfiguration if batch_size needs to be configurable.
class BatchingConfig(BaseModel):
    """Configuration for token-aware batching.

    Only exposes model_context_window as configurable.
    Other parameters (output_ratio, safety_buffer, prompt_overhead) are
    constants in token_estimation.py since they're implementation details.

    Note: Only used by v1 strategies (ExtendedContextStrategy). LLMService v2
    handles batching internally.
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

    # TODO: Post-migration cleanup - only used by v1 strategies. LLMService v2
    #   uses batch_size from its constructor. Consider removing or threading
    #   to LLMServiceFactory.
    llm_batch_size: int = Field(
        default=50, ge=1, le=200, description="Batch size for LLM processing"
    )

    llm_validation_mode: Literal["standard", "conservative", "aggressive"] = Field(
        default="standard", description="LLM validation mode"
    )

    # TODO: Post-migration cleanup - only used by v1 ExtendedContextStrategy.
    #   See BatchingConfig TODO for details.
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
