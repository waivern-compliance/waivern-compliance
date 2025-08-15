"""Source code schema for WCT.

This module defines the SourceCodeSchema class for JSON schema validation
and Pydantic models for runtime validation and type safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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


class SourceCodeDatabaseInteractionModel(BaseModel):
    """Pydantic model for source code database interactions."""

    type: str  # query, prepared_statement, orm_call, raw_sql
    line: int
    method: str | None = None
    sql_fragment: str | None = None
    contains_user_input: bool = False
    is_parameterized: bool = False


class SourceCodeDataCollectionIndicatorModel(BaseModel):
    """Pydantic model for source code data collection indicators."""

    type: str  # form_field, api_endpoint, cookie_access, session_access, file_upload, user_input
    line: int
    field_name: str | None = None
    method: str | None = None
    context: str | None = None
    potential_pii: bool = False


class SourceCodeAIMLIndicatorModel(BaseModel):
    """Pydantic model for source code AI/ML indicators."""

    type: str  # ml_library, api_call, model_file, training_code, prediction_code
    line: int
    library_name: str | None = None
    method_call: str | None = None
    context: str | None = None
    involves_personal_data: bool = False


class SourceCodeSecurityPatternModel(BaseModel):
    """Pydantic model for source code security patterns."""

    type: str  # authentication, authorization, encryption, hashing, validation, sanitization
    line: int
    method: str | None = None
    strength: str | None = None  # weak, moderate, strong
    context: str | None = None


class SourceCodeThirdPartyIntegrationModel(BaseModel):
    """Pydantic model for source code third-party integrations."""

    service_name: str
    line: int
    type: str  # api_call, sdk_usage, webhook, service_config
    endpoint: str | None = None
    data_shared: bool = False
    contains_personal_data: bool = False


class SourceCodeFileMetadataModel(BaseModel):
    """Pydantic model for source code file metadata."""

    file_size: int
    line_count: int
    last_modified: str
    complexity_score: float | None = None


class SourceCodeFileDataModel(BaseModel):
    """Pydantic model for source code file data."""

    file_path: str
    language: str
    metadata: SourceCodeFileMetadataModel
    functions: list[SourceCodeFunctionModel] = Field(default_factory=list)
    classes: list[SourceCodeClassModel] = Field(default_factory=list)
    imports: list[SourceCodeImportModel] = Field(default_factory=list)
    database_interactions: list[SourceCodeDatabaseInteractionModel] = Field(
        default_factory=list
    )
    data_collection_indicators: list[SourceCodeDataCollectionIndicatorModel] = Field(
        default_factory=list
    )
    ai_ml_indicators: list[SourceCodeAIMLIndicatorModel] = Field(default_factory=list)
    security_patterns: list[SourceCodeSecurityPatternModel] = Field(
        default_factory=list
    )
    third_party_integrations: list[SourceCodeThirdPartyIntegrationModel] = Field(
        default_factory=list
    )


class SourceCodeAnalysisMetadataModel(BaseModel):
    """Pydantic model for source code analysis metadata."""

    total_files: int
    total_lines: int
    analysis_timestamp: str
    parser_version: str


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
    def name(self) -> str:
        """Return the schema name."""
        return "source_code"

    @property
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation."""
        return self._loader.load(self.name, self.version)
