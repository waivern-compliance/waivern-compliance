"""Schema modules for Waivern Compliance Framework.

This module provides core schema abstractions and shared schemas used across
the Waivern ecosystem.

Available schemas:
- standard_input: Universal input format for connectors (MySQL, SQLite, Filesystem)
  Use: Schema("standard_input", "1.0.0")
- Base types and validation utilities used by all components
"""

from waivern_core.schemas.base import (
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
    SchemaRegistry,
)
from waivern_core.schemas.standard_input import (
    BaseMetadata,
    FilesystemMetadata,
    RelationalDatabaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_core.schemas.types import (
    AnalysesChain,
    AnalysisChainEntry,
    BaseAnalysisOutputMetadata,
    BaseFindingCompliance,
    BaseFindingEvidence,
    BaseFindingModel,
)
from waivern_core.schemas.validation import DataParsingError, parse_data_model

__all__ = [
    # Base schema infrastructure
    "JsonSchemaLoader",
    "Schema",
    "SchemaLoadError",
    "SchemaLoader",
    "SchemaRegistry",
    # Shared input schema models (used by multiple connectors)
    "StandardInputDataModel",
    "StandardInputDataItemModel",
    "BaseMetadata",
    "RelationalDatabaseMetadata",
    "FilesystemMetadata",
    # Base types and validation
    "BaseFindingModel",
    "BaseFindingCompliance",
    "BaseFindingEvidence",
    "AnalysisChainEntry",
    "AnalysesChain",
    "BaseAnalysisOutputMetadata",
    "parse_data_model",
    "DataParsingError",
]
