from typing import Any

from typing_extensions import Self, override

from wct.connectors.base import Connector
from wct.logging import get_connector_logger


class MySQLConnector(Connector[dict[str, Any]]):
    def __init__(self):
        self.logger = get_connector_logger("mysql")

    @classmethod
    @override
    def get_name(cls) -> str:
        """The name of the connector."""
        return "mysql"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create connector from configuration properties."""
        return cls()

    @override
    def extract(self, **config) -> dict[str, Any]:
        self.logger.info("Extracting data from MySQL database")
        self.logger.debug("MySQL config: %s", config)
        return {}

    @override
    def get_output_schema(self) -> type[dict[str, Any]]:
        """Return the schema this connector produces."""
        return dict[str, Any]
