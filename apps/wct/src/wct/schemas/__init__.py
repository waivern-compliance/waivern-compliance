"""WCT Schemas - Re-exports for backwards compatibility.

This module re-exports schemas from their new locations in waivern-core
and waivern-community packages.

Note: This is a compatibility layer. New code should import directly from:
- waivern_core.schemas for core schemas (StandardInputSchema, base types)
- waivern_community.connectors.*.schemas for connector schemas
- waivern_community.analysers.*.schemas for analyser output schemas
"""

# Core schemas and base types (from waivern-core)
# Analyser output schemas (from waivern-community analysers)
from waivern_community.analysers.data_subject_analyser.schemas import (
    DataSubjectFindingSchema,
)
from waivern_community.analysers.personal_data_analyser.schemas import (
    PersonalDataFindingSchema,
)
from waivern_community.analysers.processing_purpose_analyser.schemas import (
    ProcessingPurposeFindingSchema,
)

# Source code connector schema (from waivern-community)
from waivern_community.connectors.source_code.schemas import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeClassModel,
    SourceCodeClassPropertyModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
    SourceCodeFunctionModel,
    SourceCodeFunctionParameterModel,
    SourceCodeImportModel,
    SourceCodeSchema,
)
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
    StandardInputSchema,
    parse_data_model,
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
    # StandardInputSchema (from waivern-core)
    "StandardInputSchema",
    "StandardInputDataModel",
    "StandardInputDataItemModel",
    "BaseMetadata",
    "RelationalDatabaseMetadata",
    "FilesystemMetadata",
    # Analyser output schemas (from waivern-community)
    "PersonalDataFindingSchema",
    "ProcessingPurposeFindingSchema",
    "DataSubjectFindingSchema",
    # SourceCodeSchema (from waivern-community)
    "SourceCodeSchema",
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
