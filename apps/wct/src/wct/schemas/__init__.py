"""WCT Schemas - Re-exports for backwards compatibility.

This module re-exports schemas from their new locations in waivern-core
and waivern-community packages.

Note: This is a compatibility layer. New code should import directly from:
- waivern_core.schemas for core schemas (StandardInputSchema, base types)
- waivern_community.connectors.*.schemas for connector schemas
- waivern_community.analysers.*.schemas for analyser output schemas
"""

# Core schemas and base types (from waivern-core)
# Type models from standalone packages and waivern-community
from waivern_core.schemas import (
    BaseFindingModel,
    BaseMetadata,
    DataParsingError,
    FilesystemMetadata,
    JsonSchemaLoader,
    RelationalDatabaseMetadata,
    Schema,
    SchemaLoader,
    SchemaLoadError,
    StandardInputDataItemModel,
    StandardInputDataModel,
    parse_data_model,
)
from waivern_source_code.schemas import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeClassModel,
    SourceCodeClassPropertyModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
    SourceCodeFunctionModel,
    SourceCodeFunctionParameterModel,
    SourceCodeImportModel,
)

__all__ = [
    # Base infrastructure (from waivern-core)
    "JsonSchemaLoader",
    "Schema",
    "SchemaLoadError",
    "SchemaLoader",
    # Base types and validation (from waivern-core)
    "BaseFindingModel",
    "DataParsingError",
    "parse_data_model",
    # Standard input schema types (from waivern-core)
    "StandardInputDataModel",
    "StandardInputDataItemModel",
    "BaseMetadata",
    "RelationalDatabaseMetadata",
    "FilesystemMetadata",
    # Source code schema types (from waivern-community)
    "SourceCodeDataModel",
    "SourceCodeFileDataModel",
    "SourceCodeAnalysisMetadataModel",
    "SourceCodeFileMetadataModel",
    "SourceCodeFunctionModel",
    "SourceCodeFunctionParameterModel",
    "SourceCodeClassModel",
    "SourceCodeClassPropertyModel",
    "SourceCodeImportModel",
]
