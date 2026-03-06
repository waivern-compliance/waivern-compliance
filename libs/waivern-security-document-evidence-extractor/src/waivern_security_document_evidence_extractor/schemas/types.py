"""Schema data models for security document context."""

import uuid
from typing import ClassVar

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseSchemaOutput,
)
from waivern_core.types import SecurityDomain


class SecurityDocumentContextMetadata(BaseFindingMetadata):
    """Metadata for security document context items.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file path (same as filename)
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class SecurityDocumentContextModel(BaseModel):
    """Individual document context item.

    Carries the full document content and its classified security domains
    for downstream assessors. This is NOT a compliance finding — it is a
    document context carrier. It satisfies the Finding protocol (id + metadata)
    for LLMService.complete() compatibility.

    An empty security_domains list means the document is cross-cutting and
    flows to every assessor instance regardless of domain filter.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this document context item (UUID)",
    )
    filename: str = Field(
        description="Relative path within the policy documents directory",
    )
    content: str = Field(
        description="Full document text, passed verbatim to downstream LLM",
    )
    security_domains: list[SecurityDomain] = Field(
        description=(
            "Security domains this document addresses. "
            "Empty list = cross-cutting (flows to all assessors)"
        ),
    )
    metadata: SecurityDocumentContextMetadata = Field(
        description="Metadata with source file information",
    )


class SecurityDocumentContextSummary(BaseModel):
    """Summary statistics for security document context extraction."""

    total_documents: int = Field(
        ge=0, description="Total number of documents processed"
    )
    cross_cutting_count: int = Field(
        ge=0, description="Documents with empty security_domains (cross-cutting)"
    )
    domain_coverage: list[str] = Field(
        description="Distinct security domains across all documents",
    )


class SecurityDocumentContextOutput(BaseSchemaOutput):
    """Complete output structure for security_document_context schema.

    Represents the full wire format for security document context results.
    These context items feed into ISO27001Assessor instances, which receive
    documents filtered by security domain.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[SecurityDocumentContextModel] = Field(
        description="List of classified document context items",
    )
    summary: SecurityDocumentContextSummary = Field(
        description="Summary statistics of the document classification",
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the extraction process",
    )
