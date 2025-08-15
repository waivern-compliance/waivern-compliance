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
from .runbook import RunbookSchema
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
    StandardInputData,
    StandardInputDataItem,
    StandardInputDataItemMetadata,
    StandardInputSchema,
)
from .validation import DataParsingError, parse_data_model

__all__ = [
    # Base classes and utilities
    "Schema",
    "SchemaLoader",
    "JsonSchemaLoader",
    "SchemaLoadError",
    # Data parsing utilities
    "parse_data_model",
    "DataParsingError",
    # Schema classes
    "StandardInputSchema",
    "SourceCodeSchema",
    "PersonalDataFindingSchema",
    "ProcessingPurposeFindingSchema",
    "RunbookSchema",
    # Standard input type definitions
    "StandardInputData",
    "StandardInputDataItem",
    "StandardInputDataItemMetadata",
    # Source code schema
    "SourceCodeSchema",
    # Source code Pydantic models
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
