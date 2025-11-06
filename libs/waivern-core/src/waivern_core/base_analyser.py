"""Framework-level Analyser base class.

Analyser configuration is handled by application-level configuration systems.
"""

from __future__ import annotations

import abc
import inspect
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Auto-discover supported input schemas from schema_readers/ directory.

        Convention: Analysers declare input version support through file presence.
        Files in schema_readers/ directory are discovered and parsed:
        - Filename format: {schema_name}_{major}_{minor}_{patch}.py
        - Example: standard_input_1_0_0.py → Schema("standard_input", "1.0.0")

        Components can override this method for custom discovery logic.

        Returns:
            List of Schema objects representing supported input versions

        """
        # Get the directory where the component class is defined
        component_dir = Path(inspect.getfile(cls)).parent
        schema_dir = component_dir / "schema_readers"

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

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Auto-discover supported output schemas from schema_producers/ directory.

        Convention: Analysers declare output version support through file presence.
        Files in schema_producers/ directory are discovered and parsed:
        - Filename format: {schema_name}_{major}_{minor}_{patch}.py
        - Example: personal_data_finding_1_0_0.py → Schema("personal_data_finding", "1.0.0")

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

                # Parse filename: "personal_data_finding_1_0_0.py"
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
