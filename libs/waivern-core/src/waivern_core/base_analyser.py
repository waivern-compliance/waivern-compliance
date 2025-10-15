"""Framework-level Analyser base class.

Analyser configuration is handled by application-level configuration systems.
"""

from __future__ import annotations

import abc
import logging
from datetime import UTC, datetime
from typing import Any, Self

from waivern_core.message import Message
from waivern_core.schemas.base import Schema, SchemaLoadError

logger = logging.getLogger(__name__)

# Error message constants
_SCHEMA_MISMATCH_ERROR = "Message schema {message_schema} does not match expected input schema {expected_schema}"


class Analyser(abc.ABC):
    """Analysis processor that accepts schema-compliant data and produces results in defined result schemas.

    Analysers are processing components that accept input data in defined
    schema(s), run it against a specific analysis process (defined
    by the analyser itself), and then produce the analysis results in
    defined result schemas.

    Analysers behave like pure functions - they accept data in pre-defined
    input schemas and return results in pre-defined result schemas, regardless
    of the source of the data. This allows for flexible composition of analysers,
    where the output of one analyser can be used as input to another
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
        as specified in the application's configuration system.
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
        if message.schema and message.schema != expected_schema:
            raise SchemaLoadError(
                _SCHEMA_MISMATCH_ERROR.format(
                    message_schema=message.schema.name,
                    expected_schema=expected_schema.name,
                )
            )
        message.validate()

    @staticmethod
    def update_analyses_chain(
        input_message: Message, analyser_name: str
    ) -> list[dict[str, Any]]:
        """Extract existing analysis chain and add new entry with correct order.

        This method works with generic dictionary representations of chain entries,
        making it independent of specific data models. Applications can define
        their own typed models and convert to/from dicts as needed.

        Args:
            input_message: Input message that may contain existing analysis metadata
            analyser_name: Name of the current analyser to add to the chain

        Returns:
            Updated analysis chain as a list of dictionaries with the new analyser entry.
            Each dict should contain at minimum: {"order": int, "analyser": str}

        """
        existing_chain: list[dict[str, Any]] = []

        # Extract existing analysis chain from input message if present
        if hasattr(input_message.content, "get") and input_message.content.get(
            "analysis_metadata"
        ):
            metadata = input_message.content["analysis_metadata"]
            if "analyses_chain" in metadata:
                # Work with dictionaries directly for framework independence
                existing_chain = list(metadata["analyses_chain"])

        # Calculate next order number
        next_order = (
            max(entry["order"] for entry in existing_chain) + 1 if existing_chain else 1
        )

        # Create new entry and extend chain
        new_entry: dict[str, Any] = {
            "order": next_order,
            "analyser": analyser_name,
            "execution_timestamp": datetime.now(UTC),
        }
        return existing_chain + [new_entry]
