"""Schema modules for Waivern Compliance Framework.

This module provides core schema abstractions and shared schemas used across
the Waivern ecosystem.

Available schemas:
- standard_input: Universal input format for connectors (MySQL, SQLite, Filesystem)
  Use: Schema("standard_input", "1.0.0")
- Base types and validation utilities used by all components
"""

from waivern_core.schemas.connector_types import (
    BaseMetadata,
    DocumentDatabaseMetadata,
    FilesystemMetadata,
    RelationalDatabaseMetadata,
)
from waivern_core.schemas.finding_types import (
    AnalysesChain,
    AnalysisChainEntry,
    BaseAnalysisOutputMetadata,
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
    ChainEntryValidationStats,
)
from waivern_core.schemas.loader import (
    JsonSchemaLoader,
    SchemaLoader,
    SchemaLoadError,
)
from waivern_core.schemas.registry import SchemaRegistry
from waivern_core.schemas.schema import Schema
from waivern_core.schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_core.schemas.validation import DataParsingError, parse_data_model

__all__ = [
    # Base schema infrastructure
    "JsonSchemaLoader",
    "Schema",
    "SchemaLoadError",
    "SchemaLoader",
    "SchemaRegistry",
    # Connector types (input metadata)
    "BaseMetadata",
    "DocumentDatabaseMetadata",
    "FilesystemMetadata",
    "RelationalDatabaseMetadata",
    # Standard input schema models
    "StandardInputDataModel",
    "StandardInputDataItemModel",
    # Finding types (analyser output)
    "BaseFindingModel",
    "BaseFindingMetadata",
    "BaseFindingEvidence",
    "AnalysisChainEntry",
    "AnalysesChain",
    "BaseAnalysisOutputMetadata",
    "BaseSchemaOutput",
    "ChainEntryValidationStats",
    # Validation utilities
    "parse_data_model",
    "DataParsingError",
]
