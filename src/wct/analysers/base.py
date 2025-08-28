"""WCT Analyser base classes and exceptions.

Analyser configuration is handled by AnalyserConfig in the runbook module.
"""

from __future__ import annotations

import abc
import logging
from typing import Any

from typing_extensions import Self

from wct.message import Message
from wct.schemas import Schema, SchemaLoadError

logger = logging.getLogger(__name__)

# Error message constants
_SCHEMA_MISMATCH_ERROR = "Message schema {message_schema} does not match expected input schema {expected_schema}"


class Analyser(abc.ABC):
    """Analysis processor that accepts WCT schema-compliant data and produces results in the WCT-defined result schema.

    Analysers are the workers of WCT. They accept input data in WCT-defined
    schema(s), run it against a specific analysis process (defined
    by the analyser itself), and then produce the analysis results in the
    WCT-defined result schema.

    Analysers behave like pure functions - they accept data in pre-defined
    input schemas and return results in pre-defined result schemas, regardless
    of the source of the data. This allows for flexible composition of analysers
    in a runbook, where the output of one analyser can be used as input to another
    analyser, as long as the schemas match.
    """

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
        input_schema: Schema,
        output_schema: Schema,
        message: Message,
    ) -> Message:
        """Analyser-specific processing logic.

        This is the core method where the analysis happens. The analyser
        receives validated input data and returns results that will be
        automatically validated against the output schema.

        Args:
            input_schema: Input schema for data validation
            output_schema: Output schema for result validation
            message: The message to process

        Returns:
            Analysis results that conform to the analyser's output schema

        Raises:
            AnalyserError: If processing fails
            SchemaLoadError: If schema validation fails

        """

    @classmethod
    @abc.abstractmethod
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Return the input schemas supported by the analyser."""

    @classmethod
    @abc.abstractmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""

    @staticmethod
    def validate_input_message(message: Message, expected_schema: Schema) -> None:
        """Validate input message against expected schema.

        Args:
            message: Message to validate
            expected_schema: Schema the message should conform to

        Raises:
            SchemaLoadError: If schema validation fails

        """
        if message.schema and message.schema.name != expected_schema.name:
            raise SchemaLoadError(
                _SCHEMA_MISMATCH_ERROR.format(
                    message_schema=message.schema.name,
                    expected_schema=expected_schema.name,
                )
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
