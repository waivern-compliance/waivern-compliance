"""Security evidence schema types."""

import uuid
from typing import ClassVar, Literal

from pydantic import BaseModel, Field
from waivern_core import SecurityDomain
from waivern_core.schemas import BaseAnalysisOutputMetadata, BaseSchemaOutput
from waivern_core.schemas.finding_types import BaseFindingEvidence


class SecurityEvidenceMetadata(BaseModel):
    """Metadata for a security evidence item.

    Satisfies the FindingMetadata protocol via its source field, enabling
    SecurityEvidenceModel to be used directly with LLMService.complete[T, R].
    """

    source: str = Field(
        description=(
            "Where the evidence was found. For code/config: file path. "
            "For documents: document name and section reference."
        )
    )


class SecurityEvidenceModel(BaseModel):
    """A single normalised piece of security evidence.

    Unlike indicator models (which extend BaseFindingModel and carry raw
    pattern match details), SecurityEvidenceModel is a normalised hub item.
    It abstracts over the origin of the evidence — pattern-matched code,
    config file, or LLM-extracted document section — presenting a uniform
    structure to downstream assessors.

    Fields are deliberately broad to accommodate all three evidence paths:
    - CODE/CONFIG: produced by SecurityEvidenceNormaliser (no LLM)
    - DOCUMENT:    produced by DocumentEvidenceExtractor (LLM-based)

    The evidence field carries representative snippets from the source so
    downstream LLM assessors receive actual code or document excerpts
    alongside the summary description.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this evidence item (UUID)",
    )
    metadata: SecurityEvidenceMetadata = Field(
        description="Metadata about the source of this evidence item",
    )
    evidence_type: Literal["CODE", "CONFIG", "DOCUMENT"] = Field(
        description="Origin of the evidence: CODE, CONFIG, or DOCUMENT",
    )
    security_domain: SecurityDomain = Field(
        description="Security domain this evidence relates to",
    )
    polarity: Literal["positive", "negative", "neutral"] = Field(
        description=(
            "Evidence polarity: positive (good practice), "
            "negative (bad practice / gap), or neutral (presence only)"
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for this evidence item (0.0–1.0)",
    )
    description: str = Field(
        description=(
            "Evidence content. For code/config: matched excerpt or summary. "
            "For documents: verbatim section or LLM-generated summary."
        )
    )
    evidence: list[BaseFindingEvidence] = Field(
        default_factory=list,
        description=(
            "Representative snippets supporting this finding. "
            "Empty for evidence paths that do not carry raw snippets."
        ),
    )
    require_review: bool | None = Field(
        default=None,
        description=(
            "Propagated from upstream findings. True when an upstream analyser "
            "flagged the source finding as requiring human review. "
            "Causes downstream control_assessment.evidence_status = requires_attestation."
        ),
    )


class DomainBreakdown(BaseModel):
    """Per-domain breakdown of security evidence findings."""

    security_domain: str = Field(description="Security domain name")
    findings_count: int = Field(
        ge=0, description="Number of evidence items for this domain"
    )


class SecurityEvidenceSummary(BaseModel):
    """Summary statistics for a security_evidence output."""

    total_findings: int = Field(
        ge=0,
        description="Total number of security evidence items",
    )
    domains_identified: int = Field(
        ge=0,
        description="Number of distinct security domains represented in the findings",
    )
    domains: list[DomainBreakdown] = Field(
        default_factory=list,
        description="Per-domain breakdown of findings, sorted descending by findings_count",
    )


class SecurityEvidenceOutput(BaseSchemaOutput):
    """Complete output structure for security_evidence/1.0.0 schema.

    Shared hub schema produced by both SecurityEvidenceNormaliser (deterministic,
    no LLM) and DocumentEvidenceExtractor (LLM-based). Placing this in a shared
    package avoids a circular dependency between the two producer packages.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[SecurityEvidenceModel] = Field(
        description="List of normalised security evidence items",
    )
    summary: SecurityEvidenceSummary = Field(
        description="Summary statistics for this security evidence output",
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process that produced this output",
    )
