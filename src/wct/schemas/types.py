"""Shared types for WCT schemas.

This module contains base types and models that are used across
different schema definitions to ensure consistency and avoid
circular import dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator


class BaseFindingEvidence(BaseModel):
    """Evidence item with content and collection timestamp."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    content: str = Field(description="The evidence content snippet")
    collection_timestamp: Annotated[
        datetime,
        PlainSerializer(lambda v: v.isoformat(), return_type=str, when_used="json"),
    ] = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the evidence was collected",
    )


class BaseFindingCompliance(BaseModel):
    """Compliance information for findings."""

    regulation: str = Field(
        ..., min_length=1, description="Regulation name (e.g., GDPR, CCPA)"
    )
    relevance: str = Field(
        ..., min_length=1, description="Specific relevance to this regulation"
    )


class AnalysisChainEntry(BaseModel):
    """Single entry in an analysis chain tracking sequence of analysers."""

    order: int = Field(description="Sequence number in the analysis chain", ge=1)
    analyser: str = Field(description="Name of the analyser that performed this step")
    execution_timestamp: Annotated[
        datetime,
        PlainSerializer(lambda v: v.isoformat(), return_type=str, when_used="json"),
    ] = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this analysis was performed",
    )


# Type alias for analysis chain
AnalysesChain = list[AnalysisChainEntry]


class BaseAnalysisOutputMetadata(BaseModel):
    """Base metadata for analysis outputs with chain tracking."""

    model_config = ConfigDict(extra="allow")

    ruleset_used: str = Field(description="Name of the ruleset used for analysis")
    llm_validation_enabled: bool = Field(
        description="Whether LLM validation was enabled for this analysis"
    )
    evidence_context_size: str | None = Field(
        default=None, description="Size of context used for evidence extraction"
    )
    analyses_chain: AnalysesChain = Field(
        default_factory=list, description="Track the full analysis chain"
    )


class BaseFindingModel(BaseModel):
    """Base model for all finding types with mandatory common fields."""

    risk_level: str = Field(description="Risk assessment level (low, medium, high)")
    compliance: list[BaseFindingCompliance] = Field(
        min_length=1, description="Compliance information for this finding"
    )
    evidence: list[BaseFindingEvidence] = Field(
        min_length=1,
        description="Evidence items with content and timestamps for this finding",
    )
    matched_patterns: list[str] = Field(
        min_length=1,
        description="Patterns that were matched during analysis",
    )

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        """Validate risk level values."""
        allowed = ["low", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"risk_level must be one of {allowed}, got: {v}")
        return v
