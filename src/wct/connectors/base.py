import abc
from typing import Any, Generic, TypeVar

from typing_extensions import Self

from wct.errors import WCTError

_ConnectorOutputSchema = TypeVar("_ConnectorOutputSchema")


class Connector(abc.ABC, Generic[_ConnectorOutputSchema]):
    """Extracts data from sources and transforms it to WCF-defined schemas.

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
        as specified in the runbook configuration file.

        Returns:
            The connector instance

        Raises:
            ConnectorConfigError: If the configured properties are invalid
        """

    @abc.abstractmethod
    def extract(self) -> _ConnectorOutputSchema:
        """Extract data from the source and return in WCF schema format.

        This method returns data that conforms to the WCF-defined schema for this connector.

        Returns:
            Data in the connector's output schema

        Raises:
            ConnectorExtractionError: If extraction fails
        """

    @abc.abstractmethod
    def get_output_schema(self) -> type[_ConnectorOutputSchema]:
        """Return the schema this connector produces.

        Returns:
            The schema that this connector's extract() method returns
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
