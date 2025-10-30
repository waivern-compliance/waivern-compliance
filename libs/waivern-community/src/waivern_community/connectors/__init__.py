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
from waivern_mysql import MySQLConnector

from waivern_community.connectors.filesystem import (
    FilesystemConnector,
    FilesystemConnectorFactory,
)
from waivern_community.connectors.source_code import (
    SourceCodeConnector,
    SourceCodeConnectorFactory,
)
from waivern_community.connectors.sqlite import (
    SQLiteConnector,
    SQLiteConnectorFactory,
)

__all__ = (
    "Connector",
    "ConnectorConfigError",
    "ConnectorError",
    "ConnectorExtractionError",
    "FilesystemConnector",
    "FilesystemConnectorFactory",
    "MySQLConnector",
    "SourceCodeConnector",
    "SourceCodeConnectorFactory",
    "SQLiteConnector",
    "SQLiteConnectorFactory",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,
    SQLiteConnector,
)
