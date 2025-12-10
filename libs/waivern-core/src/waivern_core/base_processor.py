"""Framework-level Processor base class.

Processor is the base abstraction for all data transformation components.
Specific processor types (Analyser, Orchestrator, Synthesiser) extend this.
"""

from __future__ import annotations

import abc

from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_core.types import InputRequirement


class Processor(abc.ABC):
    """Base class for all data processors in the Waivern Compliance Framework.

    Processors are components that accept schema-compliant input data and
    produce schema-compliant output. They behave like pure functions - accepting
    data in pre-defined input schemas and returning results in pre-defined
    output schemas, regardless of the data source.

    This enables flexible composition where the output of one processor can be
    used as input to another, as long as schemas match.

    Subclasses:
        - Analyser: Analyses data for compliance findings
        - Orchestrator: Decomposes problems and spawns child runbooks (future)
        - Synthesiser: Combines findings into unified output (future)

    """

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """Get the name of the processor.

        This is used to identify the processor in the system.
        """

    @classmethod
    @abc.abstractmethod
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare valid input schema combinations for this processor.

        Each inner list represents one valid combination of inputs.
        For single-input processors, return a list with one combination.
        For multi-input processors (fan-in), return multiple combinations.

        Examples:
            # Single input processor
            return [[InputRequirement("standard_input", "1.0.0")]]

            # Multi-input processor with alternatives
            return [
                [InputRequirement("personal_data_finding", "1.0.0")],
                [InputRequirement("data_subject_finding", "1.0.0")],
            ]

            # Fan-in processor requiring multiple inputs together
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
        """Declare output schemas this processor can produce.

        Returns:
            List of Schema objects this processor can produce.

        """

    @abc.abstractmethod
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process input data and produce output.

        This is the core method where data transformation happens. The processor
        receives validated input messages and returns results that will be
        automatically validated against the output schema.

        Args:
            inputs: List of input messages to process. For single-input
                processors, this will contain one message. For fan-in
                processors, this contains multiple messages.
            output_schema: Output schema for result validation

        Returns:
            Processed results that conform to the processor's output schema

        Raises:
            ProcessorError: If processing fails
            SchemaLoadError: If schema validation fails

        """
