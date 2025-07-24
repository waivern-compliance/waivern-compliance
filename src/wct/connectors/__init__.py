from wct.connectors.base import (
    Connector,
    ConnectorConfig,
    ConnectorConfigError,
    ConnectorError,
    ConnectorExtractionError,
    PathConnectorConfig,
    SchemaInfo,
)
from wct.connectors.file import FileReaderConnector
from wct.connectors.mysql import MySQLConnector
from wct.connectors.wordpress import WordpressConnector, WordpressConnectorConfig

__all__ = (
    "Connector",
    "ConnectorConfig",
    "ConnectorConfigError",
    "ConnectorError",
    "ConnectorExtractionError",
    "FileReaderConnector",
    "MySQLConnector",
    "PathConnectorConfig",
    "SchemaInfo",
    "WordpressConnector",
    "WordpressConnectorConfig",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (FileReaderConnector, MySQLConnector, WordpressConnector)
