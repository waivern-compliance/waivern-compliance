from wct.connectors.base import (
    Connector,
    ConnectorConfig,
    ConnectorConfigError,
    ConnectorError,
    ConnectorExtractionError,
    PathConnectorConfig,
)
from wct.schema import WctSchema
from wct.connectors.file import FileConnector
from wct.connectors.mysql import MySQLConnector
from wct.connectors.wordpress import WordpressConnector, WordpressConnectorConfig

__all__ = (
    "Connector",
    "ConnectorConfig",
    "ConnectorConfigError",
    "ConnectorError",
    "ConnectorExtractionError",
    "FileConnector",
    "MySQLConnector",
    "PathConnectorConfig",
    "WctSchema",
    "WordpressConnector",
    "WordpressConnectorConfig",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (FileConnector, MySQLConnector, WordpressConnector)
