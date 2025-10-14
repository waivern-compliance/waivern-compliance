"""Waivern Compliance Framework - Core Abstractions.

This package provides the base abstractions that all Waivern components must implement.
"""

__version__ = "0.1.0"

from waivern_core.base_analyser import Analyser
from waivern_core.base_connector import Connector
from waivern_core.errors import (
    AnalyserError,
    AnalyserInputError,
    AnalyserProcessingError,
    ConnectorConfigError,
    ConnectorError,
    ConnectorExtractionError,
    MessageValidationError,
    WaivernError,
)
from waivern_core.message import Message
from waivern_core.schemas import (
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
)

__all__ = [
    # Version
    "__version__",
    # Base classes
    "Analyser",
    "Connector",
    "Message",
    "Schema",
    # Schema utilities
    "SchemaLoader",
    "JsonSchemaLoader",
    # Errors
    "WaivernError",
    "AnalyserError",
    "AnalyserInputError",
    "AnalyserProcessingError",
    "ConnectorError",
    "ConnectorConfigError",
    "ConnectorExtractionError",
    "MessageValidationError",
    "SchemaLoadError",
]
