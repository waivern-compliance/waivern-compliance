"""Base classes and configurations for WCT connectors.

This module provides:
- ConnectorConfig: Configuration dataclass for connectors in runbooks
- Connector: Abstract base class for all WCT connectors
- ConnectorError, ConnectorConfigError, ConnectorExtractionError: Exception classes
"""

import abc
import logging
from dataclasses import dataclass
from typing import Any

from typing_extensions import Self

from wct.errors import WCTError
from wct.message import Message
from wct.schemas import Schema

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConnectorConfig:
    """Configuration for a connector in a runbook."""

    name: str
    type: str
    properties: dict[str, Any]


class Connector(abc.ABC):
    """Extracts data from sources and transforms it to Waivern Compliance Framework (WCF) defined schemas.

    Connectors are the adapters between the WCF and vendor-specific software
    and services. They extract metadata and information from the source and
    transform it into the WCF-defined schema.
    """

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """Return the name of the connector."""

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
    def extract(self, output_schema: Schema) -> Message:
        """Extract data from the source and return in WCF schema format.

        This method returns data that conforms to the WCF-defined schema for this connector.

        Returns:
            Data in the connector's output schema

        Raises:
            ConnectorExtractionError: If extraction fails
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
