"""WCT Plugin base classes and exceptions."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from typing_extensions import Self

from wct.logging import get_plugin_logger
from wct.message import Message
from wct.schema import SchemaValidationError, WctSchema


@dataclass(frozen=True, slots=True)
class PluginConfig:
    """Configuration for a plugin in a runbook."""

    name: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class Plugin(abc.ABC):
    """Analysis processor that accepts WCF schema-compliant data and produces results in the WCF-defined result schema.

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

    def __init__(self) -> None:
        """Initialize the plugin with a configured logger.

        The logger is automatically set up using the plugin's class name
        in lowercase, following WCT logging conventions.
        """
        # Get the plugin name from the class and set up logger
        plugin_name = self.get_name()
        self.logger = get_plugin_logger(plugin_name)

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

    @abc.abstractmethod
    def process(
        self,
        input_schema: WctSchema[Any],
        output_schema: WctSchema[Any],
        message: Message,
    ) -> Message:
        """Plugin-specific processing logic.

        This is the core method where the analysis happens. The plugin
        receives validated input data and returns results that will be
        automatically validated against the output schema.

        Args:
            input_schema: Input data conforming to the plugin's input schema
            output_schema: Output data conforming to the plugin's output schema
            message: The message to process

        Returns:
            Analysis results that should conform to the plugin's output schema

        Raises:
            PluginError: If processing fails
        """

    @classmethod
    @abc.abstractmethod
    def get_supported_input_schemas(cls) -> list[WctSchema[Any]]:
        """Return the input schemas supported by the plugin."""

    @classmethod
    @abc.abstractmethod
    def get_supported_output_schemas(cls) -> list[WctSchema[Any]]:
        """Return the output schemas supported by this plugin."""

    @classmethod
    def validate_input_message(
        cls, message: Message, expected_schema: WctSchema[Any]
    ) -> None:
        """Validate the input message against the expected schema."""
        if message.schema and message.schema != expected_schema:
            raise SchemaValidationError(
                f"Message schema {message.schema.name} does not match expected input schema {expected_schema.name}"
            )

        message.validate()


class PluginError(Exception):
    """Base exception for plugin-related errors."""

    pass


class PluginInputError(PluginError):
    """Raised when plugin input data is invalid."""

    pass


class PluginProcessingError(PluginError):
    """Raised when plugin processing fails."""

    pass
