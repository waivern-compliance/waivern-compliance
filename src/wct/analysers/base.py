"""WCT Analyser base classes and exceptions."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from typing_extensions import Self

from wct.logging import get_analyser_logger
from wct.message import Message
from wct.schema import SchemaValidationError, WctSchema


@dataclass(frozen=True, slots=True)
class AnalyserConfig:
    """Configuration for an analyser in a runbook."""

    name: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class Analyser(abc.ABC):
    """Analysis processor that accepts WCF schema-compliant data and produces results in the WCF-defined result schema.

    Analysers are the workers of WCF. They accept input data in WCF-defined
    schema(s), run it against a specific analysis process (defined
    by the analyser itself), and then produce the analysis results in the
    WCF-defined result schema.

    Analysers behave like pure functions - they accept data in pre-defined
    input schemas and return results in pre-defined result schemas, regardless
    of the source of the data. This allows for flexible composition of analysers
    in a runbook, where the output of one analyser can be used as input to another
    analyser, as long as the schemas match.
    """

    def __init__(self) -> None:
        """Initialize the analyser with a configured logger.

        The logger is automatically set up using the analyser's class name
        in lowercase, following WCT logging conventions.
        """
        # Get the analyser name from the class and set up logger
        analyser_name = self.get_name()
        self.logger = get_analyser_logger(analyser_name)

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """Get the name of the analyser.

        This is used to identify the analyser in the system.
        """

    @classmethod
    @abc.abstractmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Instantiate this analyser from a dictionary of properties.

        The `properties` dictionary is the configuration for the analyser
        as specified in the runbook file.
        """

    @abc.abstractmethod
    def process(
        self,
        input_schema: WctSchema[Any],
        output_schema: WctSchema[Any],
        message: Message,
    ) -> Message:
        """Analyser-specific processing logic.

        This is the core method where the analysis happens. The analyser
        receives validated input data and returns results that will be
        automatically validated against the output schema.

        Args:
            input_schema: Input data conforming to the analyser's input schema
            output_schema: Output data conforming to the analyser's output schema
            message: The message to process

        Returns:
            Analysis results that should conform to the analyser's output schema

        Raises:
            AnalyserError: If processing fails
        """

    @classmethod
    @abc.abstractmethod
    def get_supported_input_schemas(cls) -> list[WctSchema[Any]]:
        """Return the input schemas supported by the analyser."""

    @classmethod
    @abc.abstractmethod
    def get_supported_output_schemas(cls) -> list[WctSchema[Any]]:
        """Return the output schemas supported by this analyser."""

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


class AnalyserError(Exception):
    """Base exception for analyser-related errors."""

    pass


class AnalyserInputError(AnalyserError):
    """Raised when analyser input data is invalid."""

    pass


class AnalyserProcessingError(AnalyserError):
    """Raised when analyser processing fails."""

    pass
