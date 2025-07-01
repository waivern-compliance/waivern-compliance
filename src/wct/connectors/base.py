from __future__ import annotations

import abc
from pathlib import Path
from typing import Any

from typing_extensions import Self


class Connector(abc.ABC):
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
        """

    @abc.abstractmethod
    def extract(self, **config) -> dict[str, Any]:
        """Extract data from the source and return in WCF schema format.

        This method takes configuration parameters and returns data that
        conforms to the WCF-defined schema for this connector.

        Args:
            **config: Configuration parameters specific to this connector

        Returns:
            Dictionary containing extracted data in the connector's output schema

        Raises:
            ConnectorError: If extraction fails
        """

    @abc.abstractmethod
    def get_output_schema(self) -> str:
        """Return the name of the schema this connector produces.

        Returns:
            The schema name that this connector's extract() method returns
        """

    @abc.abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate the configuration for this connector.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid

        Raises:
            ConnectorConfigError: If configuration is invalid
        """


class ConnectorError(Exception):
    """Base exception for connector-related errors."""

    pass


class ConnectorConfigError(ConnectorError):
    """Raised when connector configuration is invalid."""

    pass


class ConnectorExtractionError(ConnectorError):
    """Raised when data extraction fails."""

    pass


class FileConnector(Connector):
    """Extracts content and metadata from files.

    This connector can read various file types and extract their content
    and metadata for analysis by plugins.
    """

    def __init__(self):
        pass

    @classmethod
    def get_name(cls) -> str:
        return "file"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls()

    def extract(self, **config) -> dict[str, Any]:
        """Extract file content and metadata."""
        file_path = config.get("path")
        if not file_path:
            raise ConnectorExtractionError("Missing required parameter: path")

        try:
            path = Path(file_path)
            if not path.exists():
                raise ConnectorExtractionError(f"File does not exist: {file_path}")

            content = path.read_text(encoding="utf-8")

            return {
                "file_path": str(path.absolute()),
                "file_name": path.name,
                "file_size": path.stat().st_size,
                "file_extension": path.suffix,
                "content": content,
                "lines_count": len(content.splitlines()),
                "metadata": {
                    "modified_time": path.stat().st_mtime,
                    "created_time": path.stat().st_ctime,
                },
            }

        except UnicodeDecodeError as e:
            raise ConnectorExtractionError(
                f"Failed to decode file {file_path}: {e}"
            ) from e
        except Exception as e:
            raise ConnectorExtractionError(
                f"Failed to extract from file {file_path}: {e}"
            ) from e

    def get_output_schema(self) -> str:
        return "file_content"

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate that the configuration contains required parameters."""
        if "path" not in config:
            raise ConnectorConfigError("Missing required parameter: path")

        path = Path(config["path"])
        if not path.exists():
            raise ConnectorConfigError(f"File does not exist: {config['path']}")

        return True
