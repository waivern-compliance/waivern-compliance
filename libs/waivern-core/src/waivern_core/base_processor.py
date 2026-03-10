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

        Returns a list of **alternatives**, where each alternative is a list of
        **required schema types**. The Planner matches the set of schema types
        arriving from the runbook against each alternative to find a valid match.

        Key concepts:

        - **Outer list = OR (alternatives):** Each inner list is one valid way to
          invoke this processor. The Planner selects the first alternative whose
          schema types match the runbook inputs.
        - **Inner list = AND (required types):** All schema types in the inner list
          must be present in the runbook inputs for that alternative to match.
        - **Schema types, not counts:** Each ``InputRequirement`` declares a schema
          type that must be present — it does not constrain how many inputs of that
          type are provided. Multiple inputs sharing the same schema are delivered
          together via fan-in. ``process()`` receives all inputs as an unordered
          ``list[Message]`` and is responsible for partitioning by
          ``message.schema.name``.
        - **No ordering guarantee:** The ``inputs`` list passed to ``process()``
          has no guaranteed order. Partition by schema name, not by position.

        Examples:
            # Single input — accepts one schema type
            return [[InputRequirement("standard_input", "1.0.0")]]

            # Alternatives — accepts EITHER schema A OR schema B (not both)
            return [
                [InputRequirement("personal_data_finding", "1.0.0")],
                [InputRequirement("data_subject_finding", "1.0.0")],
            ]

            # Multi-schema combination — requires BOTH schema types together
            # Fan-in: multiple inputs of the same schema type are merged
            # automatically; process() receives all messages in one list
            return [
                [
                    InputRequirement("security_evidence", "1.0.0"),
                    InputRequirement("security_document_context", "1.0.0"),
                ]
            ]

            # Combination with optional schema — two alternatives:
            # 1. Both schemas together (preferred)
            # 2. Schema A alone (schema B is optional)
            return [
                [
                    InputRequirement("security_evidence", "1.0.0"),
                    InputRequirement("security_document_context", "1.0.0"),
                ],
                [InputRequirement("security_evidence", "1.0.0")],
            ]

        Returns:
            List of valid input combinations. Each combination is a list of
            InputRequirement objects declaring the required schema types.

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
