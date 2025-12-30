"""Base classes for Waivern Compliance Framework connectors.

This module provides:
- Connector: Abstract base class for all framework connectors
- Connector exceptions are defined in errors.py

Connector configuration is handled by ConnectorConfig in the runbook module.
"""

import abc
import inspect
import logging
from pathlib import Path

from waivern_core.message import Message
from waivern_core.schemas import Schema

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
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Auto-discover supported output schemas from schema_producers/ directory.

        Convention: Components declare version support through file presence.
        Files in schema_producers/ directory are discovered and parsed:
        - Filename format: {schema_name}_{major}_{minor}_{patch}.py
        - Example: standard_input_1_0_0.py → Schema("standard_input", "1.0.0")

        Components can override this method for custom discovery logic.

        Returns:
            List of Schema objects representing supported output versions

        """
        # Get the directory where the component class is defined
        component_dir = Path(inspect.getfile(cls)).parent
        schema_dir = component_dir / "schema_producers"

        schemas: list[Schema] = []

        if schema_dir.exists():
            for file in schema_dir.glob("*.py"):
                # Skip private files and __init__
                if file.name.startswith("_"):
                    continue

                # Parse filename: "standard_input_1_0_0.py"
                # Use rsplit to split from right, taking last 3 parts as version
                parts = file.stem.rsplit("_", 3)

                # Expected: [schema_name, major, minor, patch]
                expected_parts_count = 4
                if len(parts) == expected_parts_count:
                    schema_name = parts[0]
                    major, minor, patch = parts[1], parts[2], parts[3]
                    version = f"{major}.{minor}.{patch}"

                    # Create Schema object (lightweight, no file I/O)
                    schemas.append(Schema(schema_name, version))

        return schemas

    @abc.abstractmethod
    def extract(self, output_schema: Schema) -> Message:
        """Extract data from the source and return in WCF schema format.

        This method returns data that conforms to the WCF-defined schema for this connector.

        Returns:
            Data in the connector's output schema

        Raises:
            ConnectorExtractionError: If extraction fails

        """
