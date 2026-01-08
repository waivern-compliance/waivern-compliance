"""Source code schema for WCT.

This module defines the SourceCodeSchema class for JSON schema validation
and Pydantic models for runtime validation and type safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseSchemaOutput,
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
)

# Pydantic models for runtime validation and type safety


class SourceCodeFileMetadataModel(BaseModel):
    """Pydantic model for source code file metadata."""

    file_size: int
    line_count: int
    last_modified: str | None = None


class SourceCodeFileDataModel(BaseModel):
    """Pydantic model for source code file data.

    Contains raw source code for pattern matching and LLM analysis.
    Structural extraction (functions, classes) has been intentionally removed -
    LLMs understand code structure natively from raw content.
    """

    file_path: str
    language: str
    raw_content: str  # Full source code for pattern analysis and LLM validation
    metadata: SourceCodeFileMetadataModel


class SourceCodeAnalysisMetadataModel(BaseModel):
    """Pydantic model for source code analysis metadata."""

    total_files: int
    total_lines: int
    analysis_timestamp: str


class SourceCodeDataModel(BaseSchemaOutput):
    """Pydantic model for complete source code analysis data.

    This model represents the full wire format for source code analysis results.
    Extends BaseSchemaOutput for schema generation support.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    schemaVersion: str = Field(description="Schema version identifier")
    name: str = Field(description="Name of the source code analysis")
    description: str = Field(description="Description of the analysis")
    source: str = Field(description="Source path or identifier")
    metadata: SourceCodeAnalysisMetadataModel = Field(
        description="Analysis metadata including file counts and timestamp"
    )
    data: list[SourceCodeFileDataModel] = Field(
        description="List of analysed source code files"
    )


# JSON Schema class


@dataclass(frozen=True, slots=True, eq=False)
class SourceCodeSchema(Schema):
    """Schema for source code analysis data format.

    This schema represents the structured format used by source code
    connectors for analysing programming languages and extracting
    relevant compliance information.

    For runtime validation, use SourceCodeDataModel Pydantic models.
    """

    _VERSION = "1.0.0"

    # Custom loader with package-relative search path
    _loader: SchemaLoader = field(
        default_factory=lambda: JsonSchemaLoader(
            search_paths=[Path(__file__).parent / "json_schemas"]
        ),
        init=False,
    )

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "source_code"

    @property
    @override
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION

    @property
    @override
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation."""
        return self._loader.load(self.name, self.version)
