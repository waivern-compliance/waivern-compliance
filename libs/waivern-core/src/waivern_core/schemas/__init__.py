"""Schema modules for Waivern Compliance Framework.

This module provides core schema abstractions and shared schemas used across
the Waivern ecosystem.

Available schemas:
- StandardInputSchema: Universal input format for connectors (MySQL, SQLite, Filesystem)
- Base types and validation utilities used by all components
"""

from waivern_core.schemas.base import (
    BaseFindingSchema,
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
)
from waivern_core.schemas.standard_input import (
    BaseMetadata,
    FilesystemMetadata,
    RelationalDatabaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
    StandardInputSchema,
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
    "BaseFindingSchema",
    "JsonSchemaLoader",
    "Schema",
    "SchemaLoadError",
    "SchemaLoader",
    # Shared input schema (used by multiple connectors)
    "StandardInputSchema",
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
