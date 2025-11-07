"""WCT Schemas - Re-exports core schemas from waivern-core.

This module re-exports only core schemas that WCT needs. Component-specific schemas
(from connectors and analysers) are NOT re-exported here to maintain the plugin
architecture where WCT has no hardcoded knowledge of specific components.

Components register their schemas dynamically via entry points, and the SchemaRegistry
discovers them at runtime. WCT only needs to know about core base types.

Note: If you need component-specific schemas (e.g., SourceCodeDataModel,
PersonalDataFindingModel), import them directly from the component package
(e.g., from waivern_source_code.schemas import SourceCodeDataModel).
"""

# Core schemas and base types (from waivern-core only)
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
]
