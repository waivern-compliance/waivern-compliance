"""Base classes for Waivern Compliance Framework connectors.

This module provides:
- Connector: Abstract base class for all framework connectors
- Connector exceptions are defined in errors.py

Connector configuration is handled by ConnectorConfig in the runbook module.
"""

import abc
import logging

from waivern_core.message import Message
from waivern_core.schemas.base import Schema

logger = logging.getLogger(__name__)


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
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this connector.

        Returns:
            List of schemas that this connector can produce as output

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
