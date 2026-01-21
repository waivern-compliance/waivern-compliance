"""Types for analyser findings.

This module contains base types and models for analyser output,
including finding metadata and evidence.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from waivern_core.types import JsonValue


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
    context: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Extensible context for pipeline metadata (connector_type, artifact_id, etc.)",
    )


class PatternMatchDetail(BaseModel):
    """Detail about a matched pattern including occurrence count.

    This structured type replaces simple pattern strings to provide
    richer information about how many times each pattern was found,
    which is useful for auditing and confidence assessment.
    """

    pattern: str = Field(description="The pattern that matched")
    match_count: int = Field(
        ge=1, description="Number of times this pattern matched in the content"
    )


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
    matched_patterns: list[PatternMatchDetail] = Field(
        min_length=1,
        description="Patterns that were matched during analysis with occurrence counts",
    )


class BaseAnalysisOutputMetadata(BaseModel):
    """Base metadata for analysis outputs."""

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
