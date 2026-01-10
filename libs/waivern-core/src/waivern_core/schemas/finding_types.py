"""Types for analyser findings.

This module contains base types and models for analyser output,
including finding metadata, evidence, and analysis chain tracking.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, ClassVar

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


class BaseFindingMetadata(BaseModel):
    """Base metadata for all finding types.

    All analyser findings should include at minimum the source of the data
    and an extensible context for pipeline metadata.
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(description="Source file or location where the data was found")
    context: dict[str, object] = Field(
        default_factory=dict,
        description="Extensible context for pipeline metadata (connector_type, artifact_id, etc.)",
    )

    @field_validator("context")
    @classmethod
    def validate_json_serialisable(cls, v: dict[str, object]) -> dict[str, object]:
        """Ensure context is JSON-serialisable for portable storage."""
        try:
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"context must be JSON-serialisable: {e}") from e
        return v


class BaseFindingModel(BaseModel):
    """Base model for all finding types with mandatory common fields.

    Risk assessment is intentionally excluded from this base model as it is
    a framework-specific concern. Each regulatory classifier should define
    its own risk model in its output schema.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this finding (UUID)",
    )
    evidence: list[BaseFindingEvidence] = Field(
        min_length=1,
        description="Evidence items with content and timestamps for this finding",
    )
    matched_patterns: list[str] = Field(
        min_length=1,
        description="Patterns that were matched during analysis",
    )


class ChainEntryValidationStats(BaseModel):
    """LLM validation statistics for an analysis chain entry.

    Captures the impact of LLM validation on findings count.
    Only included when validation actually ran and produced results.
    """

    model_config = ConfigDict(extra="forbid")

    original_findings_count: int = Field(
        ge=0, description="Number of findings before LLM validation"
    )
    validated_findings_count: int = Field(
        ge=0, description="Number of findings after LLM validation"
    )
    false_positives_removed: int = Field(
        ge=0, description="Number of false positives removed by LLM validation"
    )
    validation_mode: str = Field(
        description="LLM validation mode used (e.g., 'standard', 'conservative')"
    )

    @classmethod
    def from_counts(
        cls,
        validation_applied: bool,
        original_count: int,
        validated_count: int,
        validation_mode: str,
    ) -> ChainEntryValidationStats | None:
        """Create validation stats from finding counts if validation was applied.

        Args:
            validation_applied: Whether LLM validation was actually applied
            original_count: Number of findings before validation
            validated_count: Number of findings after validation
            validation_mode: LLM validation mode used

        Returns:
            ChainEntryValidationStats if validation was applied, None otherwise

        """
        if not validation_applied:
            return None

        return cls(
            original_findings_count=original_count,
            validated_findings_count=validated_count,
            false_positives_removed=original_count - validated_count,
            validation_mode=validation_mode,
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
    # Optional LLM validation fields - only present when validation ran
    llm_validation_enabled: bool | None = Field(
        default=None,
        description="Whether LLM validation was enabled (only when validation ran)",
    )
    validation_statistics: ChainEntryValidationStats | None = Field(
        default=None,
        description="LLM validation statistics (only when validation ran)",
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
    analysis_timestamp: Annotated[
        datetime,
        PlainSerializer(lambda v: v.isoformat(), return_type=str, when_used="json"),
    ] = Field(
        default_factory=lambda: datetime.now(UTC),
        description="ISO 8601 timestamp when the analysis was performed",
    )
    evidence_context_size: str | None = Field(
        default=None, description="Size of context used for evidence extraction"
    )
    analyses_chain: AnalysesChain = Field(
        min_length=1, description="Track the full analysis chain"
    )

    def __init__(self, **data: object) -> None:
        """Initialize with support for extra fields."""
        super().__init__(**data)


class BaseSchemaOutput(BaseModel):
    """Base class for analyser output schemas with JSON schema generation.

    All analyser output models should extend this class to enable
    automatic JSON schema generation from Pydantic models.

    Subclasses should define __schema_version__ as a class variable:

        class MyOutput(BaseSchemaOutput):
            __schema_version__: ClassVar[str] = "1.0.0"
            findings: list[MyFinding]
            ...
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    @classmethod
    def generate_json_schema(cls, output_path: Path) -> None:
        """Generate JSON schema file from this Pydantic model.

        Args:
            output_path: Path where the JSON schema file will be written

        """
        schema = cls.model_json_schema(mode="serialization")

        # Add JSON Schema draft identifier
        schema["$schema"] = "http://json-schema.org/draft-07/schema#"

        # Use class variable for version
        if hasattr(cls, "__schema_version__"):
            schema["version"] = cls.__schema_version__

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write schema to file with trailing newline
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)
            f.write("\n")
