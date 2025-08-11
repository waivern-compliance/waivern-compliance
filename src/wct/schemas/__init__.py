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
from .source_code import SourceCodeSchema
from .standard_input import StandardInputSchema

__all__ = [
    # Base classes and utilities
    "Schema",
    "SchemaLoader",
    "JsonSchemaLoader",
    "SchemaLoadError",
    "StandardInputSchema",
    "SourceCodeSchema",
    "PersonalDataFindingSchema",
    "ProcessingPurposeFindingSchema",
]
