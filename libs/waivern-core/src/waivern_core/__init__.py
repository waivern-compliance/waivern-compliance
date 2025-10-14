"""Waivern Compliance Framework - Core Abstractions.

This package provides the base abstractions that all Waivern components must implement.
"""

__version__ = "0.1.0"

from waivern_core.base_connector import Connector
from waivern_core.errors import (
    ConnectorConfigError,
    ConnectorError,
    ConnectorExtractionError,
    MessageValidationError,
    WaivernError,
)
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseFindingSchema,
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
)

__all__ = [
    # Version
    "__version__",
    # Base classes
    "Connector",
    "Message",
    "Schema",
    "BaseFindingSchema",
    # Schema utilities
    "SchemaLoader",
    "JsonSchemaLoader",
    # Errors
    "WaivernError",
    "ConnectorError",
    "ConnectorConfigError",
    "ConnectorExtractionError",
    "MessageValidationError",
    "SchemaLoadError",
]
