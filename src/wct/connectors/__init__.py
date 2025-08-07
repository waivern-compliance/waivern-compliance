"""Data connectors package.

This package provides various connectors for extracting data from different sources
including files, databases, and web services.
"""

from wct.connectors.base import (
    Connector,
    ConnectorConfig,
    ConnectorConfigError,
    ConnectorError,
    ConnectorExtractionError,
)
from wct.connectors.filesystem import FilesystemConnector
from wct.connectors.mysql import MySQLConnector
from wct.connectors.source_code import SourceCodeConnector
from wct.connectors.wordpress import WordpressConnector, WordpressConnectorConfig
from wct.schema import WctSchema

__all__ = (
    "Connector",
    "ConnectorConfig",
    "ConnectorConfigError",
    "ConnectorError",
    "ConnectorExtractionError",
    "FilesystemConnector",
    "MySQLConnector",
    "SourceCodeConnector",
    "WctSchema",
    "WordpressConnector",
    "WordpressConnectorConfig",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,
    WordpressConnector,
)
