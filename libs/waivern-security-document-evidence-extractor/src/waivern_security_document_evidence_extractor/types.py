"""Configuration and LLM interaction types for the extractor."""

import uuid

from pydantic import BaseModel, Field
from waivern_core import BaseComponentConfiguration
from waivern_core.types import SecurityDomain
from waivern_schemas.security_document_context import SecurityDocumentContextMetadata


class SecurityDocumentEvidenceExtractorConfig(BaseComponentConfiguration):
    """Configuration for SecurityDocumentEvidenceExtractor.

    Domain vocabulary comes from the SecurityDomain enum directly —
    no ruleset config needed.
    """

    enable_llm_classification: bool = Field(
        default=True,
        description=(
            "Enable LLM-based domain classification. "
            "When False, all documents get security_domains: [] (dry-run mode)"
        ),
    )


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
