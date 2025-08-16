"""Data connectors package.

This package provides various connectors for extracting data from different sources
including files, databases, and web services.
"""

from wct.connectors.base import (
    Connector,
    ConnectorConfigError,
    ConnectorError,
    ConnectorExtractionError,
)
from wct.connectors.filesystem import FilesystemConnector
from wct.connectors.mysql import MySQLConnector
from wct.connectors.source_code import SourceCodeConnector

__all__ = (
    "Connector",
    "ConnectorConfigError",
    "ConnectorError",
    "ConnectorExtractionError",
    "FilesystemConnector",
    "MySQLConnector",
    "SourceCodeConnector",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,
)
