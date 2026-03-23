"""Schema modules for Waivern Compliance Framework.

This module provides core schema abstractions used across the Waivern ecosystem.

Schema definitions (Pydantic models and JSON schemas) live in the
waivern-schemas package. This module provides:
- Base types and validation utilities used by all components
- Schema infrastructure (registry, loader, schema descriptor)
"""

from waivern_core.schemas.finding_types import (
    BaseAnalysisOutputMetadata,
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
    PatternMatchDetail,
)
from waivern_core.schemas.loader import (
    JsonSchemaLoader,
    SchemaLoader,
    SchemaLoadError,
)
from waivern_core.schemas.registry import SchemaRegistry
from waivern_core.schemas.schema import Schema
from waivern_core.schemas.validation import DataParsingError, parse_data_model

__all__ = [
    # Base schema infrastructure
    "JsonSchemaLoader",
    "Schema",
    "SchemaLoadError",
    "SchemaLoader",
    "SchemaRegistry",
    # Finding types (analyser output)
    "BaseFindingModel",
    "BaseFindingMetadata",
    "BaseFindingEvidence",
    "BaseAnalysisOutputMetadata",
    "BaseSchemaOutput",
    "PatternMatchDetail",
    # Validation utilities
    "parse_data_model",
    "DataParsingError",
]
