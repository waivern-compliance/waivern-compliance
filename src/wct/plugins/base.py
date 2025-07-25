"""WCT Plugin base classes and exceptions."""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

import jsonschema
from typing_extensions import Self

from wct.schema import WctSchema

_PluginInputSchema = TypeVar("_PluginInputSchema")
_PluginOutputSchema = TypeVar("_PluginOutputSchema")


@dataclass(frozen=True, slots=True)
class PluginConfig:
    """Configuration for a plugin in a runbook."""

    name: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class Plugin(abc.ABC, Generic[_PluginInputSchema, _PluginOutputSchema]):
    """Analysis processor that accepts WCF schema-compliant data and
    produces results in the WCF-defined result schema.

    Plugins are the workers of WCF. They accept input data in WCF-defined
    schema(s), run it against a specific analysis process (defined
    by the plugin itself), and then produce the analysis results in the
    WCF-defined result schema.

    Plugins behave like pure functions - they accept data in pre-defined
    input schemas and return results in pre-defined result schemas, regardless
    of the source of the data. This allows for flexible composition of plugins
    in a runbook, where the output of one plugin can be used as input to another
    plugin, as long as the schemas match.
    """

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """Get the name of the plugin.

        This is used to identify the plugin in the system.
        """

    @classmethod
    @abc.abstractmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Instantiate this plugin from a dictionary of properties.

        The `properties` dictionary is the configuration for the plugin
        as specified in the runbook file.
        """

    def process(self, data: _PluginInputSchema) -> _PluginOutputSchema:
        """Process input data with automatic validation and return analysis results.

        This method automatically validates input data, processes it using the
        plugin's analysis logic, and validates the output against the declared schema.

        Args:
            data: Input data conforming to the plugin's input schema

        Returns:
            Analysis results conforming to the plugin's output schema

        Raises:
            PluginError: If processing fails
            PluginInputError: If input doesn't conform to schema
            PluginOutputError: If output doesn't conform to schema
        """
        # Validate input data
        self.validate_input(data)

        # Process the data using plugin-specific logic
        result = self.process_data(data)

        # Validate output against declared schema
        self.validate_output(result)

        return result

    @abc.abstractmethod
    def process_data(self, data: _PluginInputSchema) -> _PluginOutputSchema:
        """Plugin-specific processing logic.

        This is the core method where the analysis happens. The plugin
        receives validated input data and returns results that will be
        automatically validated against the output schema.

        Args:
            data: Input data conforming to the plugin's input schema

        Returns:
            Analysis results that should conform to the plugin's output schema

        Raises:
            PluginError: If processing fails
        """

    @abc.abstractmethod
    def get_input_schema(self) -> WctSchema[_PluginInputSchema]:
        """Return the input schema information this plugin expects.

        Returns:
            SchemaInfo containing both the schema name and type
        """

    @abc.abstractmethod
    def get_output_schema(self) -> WctSchema[_PluginOutputSchema]:
        """Return the output schema information this plugin produces.

        Returns:
            SchemaInfo containing both the schema name and type
        """

    @abc.abstractmethod
    def validate_input(self, data: _PluginInputSchema) -> bool:
        """Validate that input data conforms to the expected schema.

        Args:
            data: Input data to validate

        Returns:
            True if data is valid

        Raises:
            PluginInputError: If input data is invalid
        """

    def validate_output(self, data: _PluginOutputSchema) -> bool:
        """Validate that output data conforms to the plugin's output schema.

        Args:
            data: Output data to validate

        Returns:
            True if data is valid

        Raises:
            PluginOutputError: If output data doesn't conform to schema
        """
        output_schema = self.get_output_schema()

        try:
            # Load the JSON schema file for validation
            schema_content = self._load_json_schema(output_schema.name)

            # Validate the output against the JSON schema
            jsonschema.validate(data, schema_content)

            return True

        except jsonschema.ValidationError as e:
            raise PluginOutputError(
                f"Output validation failed for schema '{output_schema.name}': {e.message}"
            ) from e
        except FileNotFoundError:
            # Skip validation if schema file not found
            # This allows plugins to work even if schema files are missing
            return True
        except Exception as e:
            raise PluginOutputError(f"Output validation error: {e}") from e

    def _load_json_schema(self, schema_name: str) -> dict[str, Any]:
        """Load JSON schema from file.

        Args:
            schema_name: Name of the schema to load

        Returns:
            The JSON schema as a dictionary

        Raises:
            FileNotFoundError: If schema file doesn't exist
        """
        # Try multiple potential locations for schema files
        schema_paths = [
            Path("src/wct/schemas") / f"{schema_name}.json",
            Path("./src/wct/schemas") / f"{schema_name}.json",
            Path(__file__).parent.parent / "schemas" / f"{schema_name}.json",
        ]

        for schema_path in schema_paths:
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    return json.load(f)

        raise FileNotFoundError(
            f"Schema file for '{schema_name}' not found in any of: {schema_paths}"
        )


class PluginError(Exception):
    """Base exception for plugin-related errors."""

    pass


class PluginInputError(PluginError):
    """Raised when plugin input data is invalid."""

    pass


class PluginProcessingError(PluginError):
    """Raised when plugin processing fails."""

    pass


class PluginOutputError(PluginError):
    """Raised when plugin output data doesn't conform to schema."""

    pass
