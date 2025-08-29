"""Source code schema for WCT.

This module defines the SourceCodeSchema class for JSON schema validation
and Pydantic models for runtime validation and type safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, override

from pydantic import BaseModel, ConfigDict, Field

from .base import JsonSchemaLoader, Schema, SchemaLoader

# Pydantic models for runtime validation and type safety


class SourceCodeFunctionParameterModel(BaseModel):
    """Pydantic model for source code function parameters."""

    name: str
    type: str | None = None
    default_value: str | None = None


class SourceCodeFunctionModel(BaseModel):
    """Pydantic model for source code functions."""

    name: str
    line_start: int
    line_end: int
    parameters: list[SourceCodeFunctionParameterModel] = Field(default_factory=list)
    return_type: str | None = None
    visibility: str | None = None
    is_static: bool = False
    docstring: str | None = None


class SourceCodeClassPropertyModel(BaseModel):
    """Pydantic model for source code class properties."""

    name: str
    type: str | None = None
    visibility: str = "public"
    is_static: bool = False
    default_value: str | None = None


class SourceCodeClassModel(BaseModel):
    """Pydantic model for source code classes."""

    name: str
    line_start: int
    line_end: int
    extends: str | None = None
    implements: list[str] = Field(default_factory=list)
    properties: list[SourceCodeClassPropertyModel] = Field(default_factory=list)
    methods: list[SourceCodeFunctionModel] = Field(default_factory=list)


class SourceCodeImportModel(BaseModel):
    """Pydantic model for source code imports."""

    module: str
    line: int
    type: str  # require, require_once, include, include_once, use, import
    alias: str | None = None


# Analysis-related models removed - analysis now happens in analysers using rulesets
# Database interactions, data collection, AI/ML, security, and third-party patterns
# are now detected by analysers using pattern matching on raw_content


class SourceCodeFileMetadataModel(BaseModel):
    """Pydantic model for source code file metadata."""

    file_size: int
    line_count: int
    last_modified: str


class SourceCodeFileDataModel(BaseModel):
    """Pydantic model for source code file data (structural extraction only)."""

    file_path: str
    language: str
    raw_content: str  # Full source code for pattern analysis in analysers
    metadata: SourceCodeFileMetadataModel
    functions: list[SourceCodeFunctionModel] = Field(default_factory=list)
    classes: list[SourceCodeClassModel] = Field(default_factory=list)
    imports: list[SourceCodeImportModel] = Field(default_factory=list)


class SourceCodeAnalysisMetadataModel(BaseModel):
    """Pydantic model for source code analysis metadata."""

    total_files: int
    total_lines: int
    analysis_timestamp: str


class SourceCodeDataModel(BaseModel):
    """Pydantic model for complete source code analysis data."""

    schemaVersion: str
    name: str
    description: str
    language: str
    source: str
    metadata: SourceCodeAnalysisMetadataModel
    data: list[SourceCodeFileDataModel]

    model_config = ConfigDict(
        # Allow extra fields for forward compatibility
        extra="allow",
        # Use enum values for validation
        use_enum_values=True,
        # Validate assignments for runtime safety
        validate_assignment=True,
    )


# JSON Schema class


@dataclass(frozen=True, slots=True)
class SourceCodeSchema(Schema):
    """Schema for source code analysis data format.

    This schema represents the structured format used by source code
    connectors for analysing programming languages and extracting
    relevant compliance information.

    For runtime validation, use SourceCodeDataModel Pydantic models.
    """

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

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
