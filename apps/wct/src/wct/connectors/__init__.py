"""Data connectors package.

This package provides various connectors for extracting data from different sources
including files, databases, and web services.
"""

from waivern_core.base_connector import Connector
from waivern_core.errors import (
    ConnectorConfigError,
    ConnectorError,
    ConnectorExtractionError,
)

from wct.connectors.filesystem import FilesystemConnector
from wct.connectors.mysql import MySQLConnector
from wct.connectors.source_code import SourceCodeConnector
from wct.connectors.sqlite import SQLiteConnector

__all__ = (
    "Connector",
    "ConnectorConfigError",
    "ConnectorError",
    "ConnectorExtractionError",
    "FilesystemConnector",
    "MySQLConnector",
    "SourceCodeConnector",
    "SQLiteConnector",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,
    SQLiteConnector,
)
