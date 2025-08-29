"""WCT Schemas - Strongly typed schema system.

This module provides strongly typed schema classes that replace the generic
concrete, type-safe schema definitions with unified interface.

All schemas support:
- Versioned loading from json_schemas/{name}/{version}/ directories
- Version validation ensuring loaded JSON matches requested version
- Dependency injection through SchemaLoader protocol
- Comprehensive caching for performance

Available schemas:
- StandardInputSchema: General input data format
- SourceCodeSchema: Source code analysis format
- PersonalDataFindingSchema: Personal data analysis results
- ProcessingPurposeFindingSchema: GDPR processing purpose results
"""

from .base import JsonSchemaLoader, Schema, SchemaLoader, SchemaLoadError
from .personal_data_finding import PersonalDataFindingSchema
from .processing_purpose_finding import ProcessingPurposeFindingSchema
from .source_code import (
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
from .standard_input import (
    BaseMetadata,
    FilesystemMetadata,
    RelationalDatabaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
    StandardInputSchema,
)
from .validation import DataParsingError, parse_data_model

__all__ = [
    "Schema",
    "SchemaLoader",
    "JsonSchemaLoader",
    "SchemaLoadError",
    "parse_data_model",
    "DataParsingError",
    "StandardInputSchema",
    "SourceCodeSchema",
    "PersonalDataFindingSchema",
    "ProcessingPurposeFindingSchema",
    "StandardInputDataModel",
    "StandardInputDataItemModel",
    "BaseMetadata",
    "RelationalDatabaseMetadata",
    "FilesystemMetadata",
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
