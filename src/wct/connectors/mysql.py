from typing import Any

from wct.connectors.base import Connector
from wct.logging import get_connector_logger


class MySQLConnector(Connector):
    def __init__(self):
        self.logger = get_connector_logger("mysql")

    @classmethod
    def get_name(cls) -> str:
        """The name of the connector."""
        return "MySQL"

    def extract(self, **config) -> dict[str, Any]:
        self.logger.info("Extracting data from MySQL database")
        self.logger.debug("MySQL config: %s", config)
        return {}
