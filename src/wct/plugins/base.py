"""WCT Plugin base classes and exceptions."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

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
        as specified in the runbook configuration file.
        """

    @abc.abstractmethod
    def process(self, data: _PluginInputSchema) -> _PluginOutputSchema:
        """Process input data and return analysis results.

        This is the core method where the analysis happens. The plugin
        receives data in its expected input schema and returns results
        in its defined output schema.

        Args:
            data: Input data conforming to the plugin's input schema

        Returns:
            Analysis results conforming to the plugin's output schema

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


class PluginError(Exception):
    """Base exception for plugin-related errors."""

    pass


class PluginInputError(PluginError):
    """Raised when plugin input data is invalid."""

    pass


class PluginProcessingError(PluginError):
    """Raised when plugin processing fails."""

    pass
