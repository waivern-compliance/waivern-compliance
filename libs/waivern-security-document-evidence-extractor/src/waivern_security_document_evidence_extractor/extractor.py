"""Security document evidence extractor processor."""

from typing import override

from waivern_core import InputRequirement, Processor
from waivern_core.message import Message
from waivern_core.schemas import Schema


class SecurityDocumentEvidenceExtractor(Processor):
    """Classifies policy documents by security domain using LLM analysis.

    Receives standard_input/1.0.0 (from filesystem connector) containing
    policy document text, calls the LLM to classify which SecurityDomain
    values apply, and emits security_document_context/1.0.0.

    Full implementation in Step 2.
    """

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the processor."""
        return "security_document_evidence_extractor"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations."""
        return [[InputRequirement("standard_input", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this processor can produce."""
        return [Schema("security_document_context", "1.0.0")]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process policy documents and classify by security domain.

        Full implementation in Step 2.
        """
        raise NotImplementedError
