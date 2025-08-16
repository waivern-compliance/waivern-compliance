"""Type definitions for analysis runners."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from wct.analysers.utilities import EvidenceExtractor


class PatternMatchingConfig(BaseModel):
    """Strongly typed configuration for pattern matching runners."""

    ruleset: str = Field(
        default="personal_data",
        description="Name of the ruleset to use for pattern matching",
    )

    evidence_context_size: str = Field(
        default="small", description="Context size for evidence extraction"
    )

    @field_validator("evidence_context_size")
    @classmethod
    def validate_evidence_context_size(cls, v: str) -> str:
        """Validate evidence context size values."""
        allowed = ["small", "medium", "long"]
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
    """Strongly typed configuration for LLM validation runners."""

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


class PatternMatcherContext(BaseModel):
    """Strongly typed context object passed to pattern matcher functions.

    This provides a typed interface for all the context information
    that pattern matchers need to access during analysis.
    """

    # Rule information
    rule_name: str = Field(description="Name of the rule being matched")
    rule_description: str = Field(description="Description of the rule being matched")
    risk_level: str = Field(description="Risk level from the rule")

    # Analysis context
    metadata: dict[str, Any] = Field(
        description="Metadata about the content being analyzed"
    )
    config: PatternMatchingConfig = Field(
        description="Configuration for the pattern matching analysis"
    )

    # Utilities
    evidence_extractor: EvidenceExtractor = Field(
        description="Utility for extracting evidence snippets from content"
    )

    model_config = {"arbitrary_types_allowed": True}
