"""ISO 27001 control assessor."""

from typing import override

from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import LLMService

from .types import ISO27001AssessorConfig


class ISO27001Assessor(Analyser):
    """Assessor for individual ISO 27001 controls.

    Each instance assesses exactly one control (identified by control_ref).
    Receives security evidence and optional document context as inputs,
    filters by security domain, derives evidence_status, and calls the
    LLM to produce a structured assessment verdict.

    Two input alternatives are supported:
    1. security_evidence + security_document_context (full assessment)
    2. security_evidence only (attestation-required controls emit not_assessed)
    """

    def __init__(
        self,
        config: ISO27001AssessorConfig,
        llm_service: LLMService,
    ) -> None:
        """Initialise the assessor with dependency injection.

        Args:
            config: Validated configuration with control_ref and ruleset URI.
            llm_service: LLM service for assessment verdicts.

        """
        self._config = config
        self._llm_service = llm_service

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the assessor."""
        return "iso27001_assessor"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        Two alternatives:
        1. Both security_evidence and security_document_context (full pipeline)
        2. security_evidence only (no document context available yet)

        The first alternative is preferred when document context is available.
        The second allows technical-only assessment where attestation-required
        controls emit requires_attestation status.
        """
        return [
            [
                InputRequirement("security_evidence", "1.0.0"),
                InputRequirement("security_document_context", "1.0.0"),
            ],
            [InputRequirement("security_evidence", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this assessor can produce."""
        return [Schema("iso27001_assessment", "1.0.0")]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Assess a single ISO 27001 control against provided evidence.

        Orchestrates the complete assessment flow:
        1. Partition inputs by schema (security_evidence vs document_context)
        2. Load matching rule from iso27001_domains ruleset
        3. Filter evidence by security_domains intersection
        4. Derive evidence_status (may short-circuit without LLM)
        5. Build LLM prompt with filtered evidence and document context
        6. Parse LLM response into structured assessment verdict

        Args:
            inputs: Input messages (security_evidence and/or document_context).
            output_schema: Expected output schema (iso27001_assessment/1.0.0).

        Returns:
            Output message with ISO27001AssessmentModel findings.

        """
        raise NotImplementedError("process() will be implemented in Steps 4-5")
