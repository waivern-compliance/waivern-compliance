import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from typing_extensions import Self

from wct.errors import WCTError
from wct.schema import WctSchema

_ConnectorOutputSchema = TypeVar("_ConnectorOutputSchema")


@dataclass(frozen=True, slots=True)
class ConnectorConfig:
    """Configuration for a connector in a runbook."""

    name: str
    type: str
    properties: dict[str, Any]


class PathConnectorConfig(BaseModel):
    """A shortcut configuration for `file_reader` or
    `directory` connector, requiring only a path."""

    path: Path

    def to_connector_config(self) -> ConnectorConfig:
        """Convert to a full `ConnectorConfig`."""
        if self.path.is_file():
            connector_name = f"file_{self.path.name}"
            return ConnectorConfig(
                name=connector_name,
                type="file",
                properties={"path": self.path},
            )
        elif self.path.is_dir():
            connector_name = f"dir_{self.path.name}"
            return ConnectorConfig(
                name=connector_name,
                type="directory",
                properties={"path": self.path},
            )
        else:
            raise FileNotFoundError(self.path)


class Connector(abc.ABC, Generic[_ConnectorOutputSchema]):
    """Extracts data from sources and transforms it to Waivern
    Compliance Framework (WCF) defined schemas.

    Connectors are the adapters between the WCF and vendor-specific software
    and services. They extract metadata and information from the source and
    transform it into the WCF-defined schema.
    """

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """The name of the connector."""

    @classmethod
    @abc.abstractmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Instantiate this connector from a dictionary of properties.

        The `properties` dictionary is the configuration for the connector
        as specified in the runbook file.

        Returns:
            The connector instance

        Raises:
            ConnectorConfigError: If the configured properties are invalid
        """

    @abc.abstractmethod
    def extract(
        self, schema: WctSchema[_ConnectorOutputSchema]
    ) -> _ConnectorOutputSchema:
        """Extract data from the source and return in WCF schema format.

        This method returns data that conforms to the WCF-defined schema for this connector.

        Returns:
            Data in the connector's output schema

        Raises:
            ConnectorExtractionError: If extraction fails
        """

    @abc.abstractmethod
    def get_output_schema(self) -> WctSchema[_ConnectorOutputSchema]:
        """Return the schema information this connector produces.

        Returns:
            SchemaInfo containing both the schema name and type
        """


class ConnectorError(WCTError):
    """Base exception for connector-related errors."""

    pass


class ConnectorConfigError(ConnectorError):
    """Raised when connector configuration is invalid."""

    pass


class ConnectorExtractionError(ConnectorError):
    """Raised when data extraction fails."""

    pass
