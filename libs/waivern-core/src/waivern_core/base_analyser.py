"""Framework-level Analyser base class.

Analyser configuration is handled by application-level configuration systems.
"""

from __future__ import annotations

import abc

from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_core.types import InputRequirement


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
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare valid input schema combinations for this analyser.

        Each inner list represents one valid combination of inputs.
        For single-input analysers, return a list with one combination.
        For multi-input analysers (fan-in), return multiple combinations.

        Examples:
            # Single input analyser
            return [[InputRequirement("standard_input", "1.0.0")]]

            # Multi-input analyser with alternatives
            return [
                [InputRequirement("personal_data_finding", "1.0.0")],
                [InputRequirement("data_subject_finding", "1.0.0")],
            ]

            # Fan-in analyser requiring multiple inputs together
            return [
                [
                    InputRequirement("personal_data_finding", "1.0.0"),
                    InputRequirement("data_subject_finding", "1.0.0"),
                ]
            ]

        Returns:
            List of valid input combinations. Each combination is a list of
            InputRequirement objects.

        """

    @classmethod
    @abc.abstractmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this analyser can produce.

        Returns:
            List of Schema objects this analyser can produce.

        """

    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        """Declare compliance frameworks this component's output supports.

        Returns:
            List of framework identifiers (e.g., ["GDPR", "UK_GDPR"]),
            or empty list for generic/framework-agnostic components.

        """
        return []

    @abc.abstractmethod
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Analyser-specific processing logic.

        This is the core method where the analysis happens. The analyser
        receives validated input messages and returns results that will be
        automatically validated against the output schema.

        Args:
            inputs: List of input messages to process. For single-input
                analysers, this will contain one message. For fan-in
                analysers, this contains multiple messages.
            output_schema: Output schema for result validation

        Returns:
            Analysis results that conform to the analyser's output schema

        Raises:
            AnalyserError: If processing fails
            SchemaLoadError: If schema validation fails

        """
