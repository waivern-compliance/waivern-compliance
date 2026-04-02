"""Configuration and LLM interaction types for the extractor."""

import uuid

from pydantic import BaseModel, Field
from waivern_core import BaseComponentConfiguration
from waivern_schemas.security_document_context import SecurityDocumentContextMetadata
from waivern_schemas.security_domain import SecurityDomain


class SecurityDocumentEvidenceExtractorConfig(BaseComponentConfiguration):
    """Configuration for SecurityDocumentEvidenceExtractor.

    Domain vocabulary comes from the SecurityDomain enum directly —
    no ruleset config needed. LLM availability is determined by service
    injection, not configuration.
    """


class DocumentItem(BaseModel):
    """Lightweight document item satisfying the Finding protocol.

    Used as the item type for LLMService.complete() — provides the
    id and metadata.source required by the Finding protocol, without
    carrying the full document content (which goes in ItemGroup.content).
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this document item (UUID)",
    )
    metadata: SecurityDocumentContextMetadata = Field(
        description="Metadata with source file information",
    )


class SecurityDocEvidencePrepareState(BaseModel):
    """Intermediate state produced by prepare(), consumed by finalise().

    Captures everything finalise() needs to build the output message,
    independent of whether LLM dispatch occurred.
    """

    document_items: list[DocumentItem]
    document_contents: list[str]
    llm_enabled: bool
    run_id: str


class DomainClassificationResponse(BaseModel):
    """LLM response model for domain classification.

    The LLM returns which SecurityDomain values apply to a document,
    or an empty list for cross-cutting documents. It also returns a
    compliance-focused summary preserving key controls, procedures,
    and requirements while discarding boilerplate.
    """

    security_domains: list[SecurityDomain] = Field(
        description=(
            "Security domains this document addresses. "
            "Empty list = cross-cutting (applies to all domains)"
        ),
    )
    summary: str = Field(
        description=(
            "Compliance-focused summary of the document preserving key "
            "controls, procedures, responsibilities, and requirements"
        ),
    )
