"""Types for LLM-based validation configuration."""

from typing import Literal

from pydantic import BaseModel, Field


class LLMValidationConfig(BaseModel):
    """Strongly typed configuration for LLM validation analysis."""

    enable_llm_validation: bool = Field(
        default=False,
        description="Whether to enable LLM-based validation to filter false positives",
    )

    llm_validation_mode: Literal["standard", "conservative", "aggressive"] = Field(
        default="standard", description="LLM validation mode"
    )

    sampling_size: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Number of samples per group for sampling-based validation. "
        "Defaults to 3 to limit LLM API costs.",
    )
