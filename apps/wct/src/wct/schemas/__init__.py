"""WCT Schemas - Re-exports core schemas from waivern-core.

This module re-exports only core schemas that WCT needs. Component-specific schemas
(from connectors and analysers) are NOT re-exported here to maintain the plugin
architecture where WCT has no hardcoded knowledge of specific components.

Components register their schemas dynamically via entry points, and the SchemaRegistry
discovers them at runtime. WCT only needs to know about core base types.

Note: If you need component-specific schemas (e.g., SourceCodeDataModel,
PersonalDataFindingModel), import them directly from the component package
(e.g., from waivern_source_code_analyser.schemas import SourceCodeDataModel).
"""

# Core schemas and base types (from waivern-core only)
from waivern_core.schemas import (
    BaseFindingModel,
    DataParsingError,
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
    parse_data_model,
)
from waivern_schemas.connector_types import (
    BaseMetadata,
    FilesystemMetadata,
    RelationalDatabaseMetadata,
)
from waivern_schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
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
    # Standard input schema types (from waivern-schemas)
    "StandardInputDataModel",
    "StandardInputDataItemModel",
    "BaseMetadata",
    "RelationalDatabaseMetadata",
    "FilesystemMetadata",
]
